"""Audit AI Trading V1 completion boundaries from local evidence.

This script does not call models, exchanges, GitHub, or order backends. It reads
the checked-in acceptance/status/memory documents and reports whether the local
V1 track is accepted, while keeping production/live-order work explicitly
pending until real external evidence exists.

Run from backend:

    uv run python scripts/ai_trading_v1_completion_audit.py --strict-local

Use --strict-production only for a production cutover audit. It intentionally
fails unless a complete sanitized production evidence file is supplied and the
caller also passes --allow-live-ready-from-evidence.

Use --explain-production-evidence to print an item-level, non-secret operations
checklist for filling or fixing the external production evidence file.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION = "hyperalpha.ai_trading.external_acceptance.v1"
EXPECTED_LOCAL_DEVELOPMENT_BRANCH = "codex/ai-agent-multitenant-foundation"
SAFE_ARTIFACT_REF_SCHEMES = {"https", "ops", "lark", "notion"}
ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS = {
    "version",
    "generated_at",
    "secret_values_returned",
    "notes",
    "items",
}
ALLOWED_PRODUCTION_EVIDENCE_ITEM_FIELDS = {
    "status",
    "validated_at",
    "validated_by",
    "evidence_summary",
    "artifact_refs",
    "secret_values_returned",
}
MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS = 24
MAX_PRODUCTION_EVIDENCE_SUMMARY_CHARS = 600
MAX_PRODUCTION_EVIDENCE_VALIDATOR_CHARS = 120
MAX_PRODUCTION_EVIDENCE_NOTE_CHARS = 300
MAX_PRODUCTION_EVIDENCE_NOTES = 12
MAX_PRODUCTION_EVIDENCE_ARTIFACT_REF_CHARS = 300
MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS = 5
PLACEHOLDER_EVIDENCE_VALUES = {
    "-",
    "accepted",
    "change me",
    "change-me",
    "changeme",
    "done",
    "fill me",
    "fill-me",
    "n/a",
    "na",
    "none",
    "ok",
    "pending",
    "placeholder",
    "tbd",
    "test",
    "todo",
    "unknown",
}
PRODUCTION_EVIDENCE_TEMPLATE_NOTES = (
    "Copy this file outside the code repository or into a private ops evidence location before filling it; repo-local production evidence files cannot unlock live-order readiness.",
    "Do not include API keys, bearer tokens, database URLs, private keys, raw Authorization headers, or user secrets.",
    "Use only documented evidence schema fields. Allowed root fields are version, generated_at, secret_values_returned, notes, and items. Allowed item fields are status, validated_at, validated_by, evidence_summary, artifact_refs, and secret_values_returned. Unknown root or item fields are rejected.",
    "Root notes are optional and must be a bounded list of concise strings; do not use notes for raw logs, model output, traces, or pasted operational dumps.",
    "The items object must contain only the documented external acceptance item ids in this template; unknown item ids are rejected.",
    "generated_at and every item validated_at must be timezone-aware ISO-8601 timestamps, for example 2026-06-10T12:00:00Z; generated_at must not be earlier than any item validated_at.",
    "artifact_refs must be non-empty sanitized references using https://, ops://, lark://, or notion:// only; use no more than 5 refs per item, keep each ref at 300 characters or less, and do not embed credentials or point to localhost/private-network URLs.",
    "Each item must become status=accepted with validated_at, a non-placeholder validated_by of 3-120 characters, a concrete evidence_summary of 24-600 characters, artifact_refs, and secret_values_returned=false before production cutover audit can pass.",
)
PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS = (
    "status=accepted",
    "validated_at=timezone-aware ISO-8601 timestamp",
    "validated_by=non-placeholder reviewer/operator name, 3-120 chars",
    "evidence_summary=concrete sanitized acceptance summary, 24-600 chars",
    "artifact_refs=1-5 safe refs using https://, ops://, lark://, or notion://",
    "secret_values_returned=false",
)
PRODUCTION_EVIDENCE_COMMON_FORBIDDEN = (
    "API keys",
    "bearer tokens",
    "database URLs",
    "private keys",
    "raw Authorization headers",
    "raw model output",
    "raw operational dumps",
)
PRODUCTION_EVIDENCE_ITEM_GUIDANCE: dict[str, tuple[str, ...]] = {
    "macos_reboot_recovery": (
        "After a real macOS reboot, prove LaunchAgent restored frontend, backend, mock gateway, and Postgres readiness.",
        "Use ai_trading_v1_env_check.py --strict --require-runtime-mirror-current as the sanitized readiness artifact.",
    ),
    "real_model_profile_live_acceptance": (
        "Configure a user's Hyper AI profile with DeepSeek or Qwen credentials outside the evidence file.",
        "Run ai_trading_model_adjust_live_acceptance.py with explicit live-model confirmation and record only sanitized outcome metadata.",
    ),
    "real_order_backend_handoff": (
        "Configure the real HTTPS order-backend signal gateway and token outside the evidence file.",
        "Run the production handoff checker and capture sanitized proof that the gateway is external, token-present, and explicitly approved.",
    ),
    "production_auth_hard_risk_readiness": (
        "Validate production Auth/JWKS, issuer, audience, algorithms, hard TP/SL/notional/leverage caps, and production handoff approval.",
        "Use production readiness output that confirms no token, API key, DB URL, or raw authorization value is returned.",
    ),
    "admin_readiness_real_auth_visual": (
        "Under real auth, verify an admin/operator can see the Settings AI Trading production readiness panel.",
        "Record a sanitized visual artifact reference without cookies, tokens, or raw API responses.",
    ),
    "production_agent_session_visual": (
        "Under real production login, verify the agent-session detail page renders only the current user's session audit/context budget.",
        "Record a sanitized visual artifact reference proving no raw context_summary secrets are rendered.",
    ),
    "real_exchange_execution": (
        "Run this as a separate production live-trading acceptance outside local V1.",
        "Record only bounded sanitized execution evidence after the order backend, not the AI agent, performs the exchange action.",
    ),
}
SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\b(api[_-]?key|password|private[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*['\"]?[^'\"\s,}]{4,}", re.IGNORECASE),
    re.compile(r"\bsecret\s*[:=]\s*['\"]?[^'\"\s,}]{4,}", re.IGNORECASE),
    re.compile(r"\bpostgres(?:ql)?://[^\s'\"]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


@dataclass(frozen=True)
class EvidenceRequirement:
    id: str
    track: str
    description: str
    path: str
    required_phrases: tuple[str, ...] = ()
    required_patterns: tuple[str, ...] = ()
    status_if_present: str = "accepted"
    metadata: dict[str, Any] = field(default_factory=dict)


LOCAL_REQUIREMENTS: tuple[EvidenceRequirement, ...] = (
    EvidenceRequirement(
        id="aggregate_local_acceptance_runner",
        track="local_v1",
        description="One-key local acceptance runner covers tests, frontend build, runtime readiness, mock handoff, and DB-audit readiness blocker.",
        path="scripts/local-dev/run_ai_trading_v1_local_acceptance.sh",
        required_phrases=(
            "--confirm-local-mock-handoff",
            "Default production readiness DB-audit gate remains blocked",
            "--include-db-audits",
            "Frontend build",
            "tests/test_ai_trading_frontend_readiness_source.py",
            "local completion summary gate",
            "git_governance.status",
            "ready_for_live_orders_false",
            "deferred_by_user_request",
            "codex/ai-agent-multitenant-foundation",
            "ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff",
            "Production evidence template remains blocked",
            "Production evidence explain mode gate",
            "--explain-production-evidence",
            "production_evidence_explain_gate",
            "Production evidence initializer gate",
            "--init-production-evidence-file",
            "production_evidence_initializer_gate",
            "real_order_backend_blocked",
            "Local LaunchAgent runtime sync",
            "scripts/local-dev/install_launch_agent.sh",
            "--require-runtime-mirror-current",
            "Runtime readiness attempt",
            "run_runtime_readiness_with_retry",
            "--production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production",
        ),
    ),
    EvidenceRequirement(
        id="acceptance_checklist_latest_local_proof",
        track="local_v1",
        description="V1 checklist records the latest local acceptance proof and separates unfinished real-environment work.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=(
            "一键本地 V1 验收通过",
            "默认生产 DB-audit readiness gate 阻断",
            "当前未验收",
            "真实 DeepSeek/Qwen API key live model-adjust 未验收",
            "真实 HyperAlpha 订单后端 URL/token live handoff 未验收",
            "真实交易所执行不属于 V1 本地验收完成条件",
        ),
        required_patterns=(
            r"spec `#\d+`",
            r"signal event `#\d+`",
            r"agent_sessions\.total=\d+",
            r"handoff_attempts\.total=\d+",
        ),
    ),
    EvidenceRequirement(
        id="status_progress_marker",
        track="local_v1",
        description="Feature status marks the local admin production evidence explain API as accepted and remote push as skipped.",
        path="docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md",
        required_phrases=(
            "Local V1 Admin Production Evidence Explain API Accepted / Remote Push Skipped",
            "| AI Trading aggregate acceptance DB-audit gate | Done |",
            "| AI Trading V1 completion boundary audit | Done |",
            "| AI Trading production evidence gate | Done |",
            "| AI Trading production evidence text quality | Done |",
            "| AI Trading production evidence text bounds | Done |",
            "| AI Trading production evidence artifact-ref bounds | Done |",
            "| AI Trading production evidence item IDs | Done |",
            "| AI Trading production evidence path safety | Done |",
            "| AI Trading production evidence note safety | Done |",
            "| AI Trading production evidence initializer | Done |",
            "| AI Trading aggregate production evidence initializer gate | Done |",
            "| AI Trading production evidence explain mode | Done |",
            "| AI Trading aggregate production evidence explain gate | Done |",
            "| AI Trading admin production evidence explain API | Done |",
            "| AI Trading runtime mirror freshness gate | Done |",
            "| AI Trading runtime readiness cold-start retry | Done |",
            "| AI Trading agent-session manual context secret rejection | Done |",
            "| AI Trading env-check runtime context budget gate | Done |",
            "| AI Trading runtime budget UI source guard | Done |",
            "| AI Trading completion audit git governance gate | Done |",
            "| AI Trading local completion summary gate | Done |",
            "| Remote push | Deferred | GitHub upload intentionally skipped per user request |",
        ),
    ),
    EvidenceRequirement(
        id="signal_only_gateway_contract",
        track="safety",
        description="Gateway contract keeps AI Trading signal-only and requires the order backend to be the only real order authority.",
        path="docs/hyperalpha/ai-trading-signal-gateway-contract.md",
        required_phrases=(
            "AI Trading emits reviewed trade signals only",
            "AI agent and AI Trading API must not place exchange orders directly",
            "order_backend_only",
            "not_an_order=true",
            "ai_may_place_orders=false",
            "requires_user_confirmation=true",
            "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
        ),
    ),
    EvidenceRequirement(
        id="development_governance",
        track="governance",
        description="Development governance requires memory compression, testing before acceptance, and branch separation.",
        path="docs/hyperalpha/development-governance.zh-CN.md",
        required_phrases=(
            "先做上下文记忆压缩，再开发",
            "测试未通过不能验收",
            "未验收不能标记完成",
            "GitHub 上传必须走分支管理，不直接合并",
            "implemented != done",
            "accepted 才能进入完成清单",
        ),
    ),
)


EXTERNAL_REQUIREMENTS: tuple[EvidenceRequirement, ...] = (
    EvidenceRequirement(
        id="macos_reboot_recovery",
        track="external_acceptance",
        description="Physical macOS reboot recovery must be proven outside the current local session.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("实际 macOS 整机重启后的自动恢复还未物理验收",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="real_model_profile_live_acceptance",
        track="external_acceptance",
        description="Real DeepSeek/Qwen model-adjust must be accepted with a user Hyper AI profile/API key.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实 DeepSeek/Qwen API key live model-adjust 未验收",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="real_order_backend_handoff",
        track="external_acceptance",
        description="Real HyperAlpha order-backend URL/token handoff must be accepted before production live orders.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实 HyperAlpha 订单后端 URL/token live handoff 未验收",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="production_auth_hard_risk_readiness",
        track="external_acceptance",
        description="Production Auth/JWKS, hard-risk values, and handoff approval must be validated with real deployment config.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实 HTTPS 订单后端 URL/token、真实 Auth/JWKS、硬风控生产值",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="admin_readiness_real_auth_visual",
        track="external_acceptance",
        description="Settings Admin readiness panel must be visually accepted under real auth/admin login.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实登录态/真实 Auth 配置下的可视化验收未做",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="production_agent_session_visual",
        track="external_acceptance",
        description="Agent-session detail page must be accepted under real production login state.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实生产登录态下的 session 详情页验收另行处理",),
        status_if_present="pending_external_acceptance",
    ),
    EvidenceRequirement(
        id="real_exchange_execution",
        track="external_acceptance",
        description="Real exchange execution is outside local V1 and must use a separate production live-trading acceptance.",
        path="docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        required_phrases=("真实交易所执行不属于 V1 本地验收完成条件",),
        status_if_present="out_of_local_v1_scope",
    ),
)


def _read_text(repo_root: Path, relative_path: str) -> str | None:
    path = repo_root / relative_path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _evaluate_requirement(repo_root: Path, requirement: EvidenceRequirement) -> dict[str, Any]:
    text = _read_text(repo_root, requirement.path)
    missing_phrases: list[str] = []
    missing_patterns: list[str] = []
    if text is None:
        missing_phrases = list(requirement.required_phrases)
        missing_patterns = list(requirement.required_patterns)
        status = "missing_evidence_file"
    else:
        missing_phrases = [phrase for phrase in requirement.required_phrases if phrase not in text]
        missing_patterns = [pattern for pattern in requirement.required_patterns if re.search(pattern, text) is None]
        status = requirement.status_if_present if not missing_phrases and not missing_patterns else "incomplete_evidence"

    return {
        "id": requirement.id,
        "track": requirement.track,
        "description": requirement.description,
        "status": status,
        "path": requirement.path,
        "missing_phrases": missing_phrases,
        "missing_patterns": missing_patterns,
        **requirement.metadata,
    }


def _latest_memory_report(repo_root: Path) -> dict[str, Any]:
    latest_path = "docs/hyperalpha/memory/latest.md"
    latest_text = _read_text(repo_root, latest_path)
    if latest_text is None:
        return {
            "id": "latest_memory_pointer",
            "track": "governance",
            "status": "missing_evidence_file",
            "path": latest_path,
            "description": "latest.md must point to the latest compressed development memory.",
            "missing_phrases": ["Current:"],
            "missing_patterns": [],
        }

    match = re.search(r"Current:\s*`?([^`\n]+)`?", latest_text)
    memory_file = match.group(1).strip() if match else ""
    memory_path = f"docs/hyperalpha/memory/{memory_file}" if memory_file else ""
    memory_text = _read_text(repo_root, memory_path) if memory_path else None
    required_memory_phrases = (
        "GitHub 上传：按用户要求跳过",
        EXPECTED_LOCAL_DEVELOPMENT_BRANCH,
        "不 push、不 merge",
        "default production readiness DB-audit blocker",
        "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
        "真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key",
    )
    missing_phrases = ["Current:"] if not match else []
    if memory_text is None:
        status = "missing_evidence_file"
        missing_phrases.extend(required_memory_phrases)
    else:
        missing_phrases.extend([phrase for phrase in required_memory_phrases if phrase not in memory_text])
        status = "accepted" if not missing_phrases else "incomplete_evidence"

    return {
        "id": "latest_memory_pointer",
        "track": "governance",
        "description": "latest.md points to compressed memory that records the latest local acceptance and external blockers.",
        "status": status,
        "path": latest_path,
        "memory_path": memory_path or None,
        "missing_phrases": missing_phrases,
        "missing_patterns": [],
    }


def _read_git_branch(repo_root: Path) -> dict[str, Any]:
    git_metadata_path = repo_root / ".git"
    if not git_metadata_path.exists():
        return {"branch": None, "detached": False, "metadata_available": False}

    git_dir = git_metadata_path
    if git_metadata_path.is_file():
        gitdir_text = git_metadata_path.read_text(encoding="utf-8", errors="replace").strip()
        if not gitdir_text.startswith("gitdir:"):
            return {"branch": None, "detached": False, "metadata_available": False}
        git_dir = (repo_root / gitdir_text.removeprefix("gitdir:").strip()).resolve()

    head_path = git_dir / "HEAD"
    try:
        head_text = head_path.read_text(encoding="utf-8", errors="replace").strip()
    except FileNotFoundError:
        return {"branch": None, "detached": False, "metadata_available": False}

    if head_text.startswith("ref: refs/heads/"):
        return {
            "branch": head_text.removeprefix("ref: refs/heads/"),
            "detached": False,
            "metadata_available": True,
        }
    return {"branch": None, "detached": bool(head_text), "metadata_available": True}


def _git_governance_report(repo_root: Path) -> dict[str, Any]:
    branch_report = _read_git_branch(repo_root)
    acceptance_text = _read_text(repo_root, "docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md") or ""
    status_text = _read_text(repo_root, "docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md") or ""
    latest_memory = _latest_memory_report(repo_root)
    memory_path = latest_memory.get("memory_path")
    memory_text = _read_text(repo_root, str(memory_path)) if memory_path else ""
    memory_text = memory_text or ""
    blockers: list[str] = []

    if not branch_report["metadata_available"]:
        blockers.append("git_metadata_unavailable")
    elif branch_report["detached"]:
        blockers.append("detached_head")
    elif branch_report["branch"] != EXPECTED_LOCAL_DEVELOPMENT_BRANCH:
        blockers.append("unexpected_branch")

    if f"`{EXPECTED_LOCAL_DEVELOPMENT_BRANCH}` 分支本地提交" not in acceptance_text:
        blockers.append("acceptance_checklist_missing_local_branch_boundary")
    if "GitHub 上传按当前用户要求暂不处理" not in acceptance_text:
        blockers.append("acceptance_checklist_missing_github_upload_deferred_boundary")
    if f"Branch: `{EXPECTED_LOCAL_DEVELOPMENT_BRANCH}`" not in status_text:
        blockers.append("status_missing_expected_branch")
    if "| Remote push | Deferred | GitHub upload intentionally skipped per user request |" not in status_text:
        blockers.append("status_missing_remote_push_deferred")
    if EXPECTED_LOCAL_DEVELOPMENT_BRANCH not in memory_text or "不 push、不 merge" not in memory_text:
        blockers.append("latest_memory_missing_branch_or_no_push_boundary")

    return {
        "id": "git_governance",
        "track": "governance",
        "description": "Local V1 must stay on the approved codex branch, with GitHub upload deferred and no merge/push boundary recorded.",
        "status": "accepted" if not blockers else "incomplete_evidence",
        "path": ".git/HEAD",
        "expected_branch": EXPECTED_LOCAL_DEVELOPMENT_BRANCH,
        "current_branch": branch_report["branch"],
        "detached": branch_report["detached"],
        "github_upload": "deferred_by_user_request",
        "blockers": blockers,
        "missing_phrases": [],
        "missing_patterns": [],
    }


def _secret_pattern_hits(value: Any) -> list[str]:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    hits: list[str] = []
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(serialized):
            hits.append(pattern.pattern)
    return hits


def _artifact_ref_blockers(ref: Any) -> list[str]:
    if not isinstance(ref, str) or not ref.strip():
        return ["external_evidence_artifact_ref_must_be_non_empty_string"]
    if len(ref.strip()) > MAX_PRODUCTION_EVIDENCE_ARTIFACT_REF_CHARS:
        return ["external_evidence_artifact_ref_too_long"]
    if _secret_pattern_hits(ref):
        return ["external_evidence_artifact_ref_secret_pattern_detected"]

    parsed = urlparse(ref)
    blockers: list[str] = []
    if parsed.scheme not in SAFE_ARTIFACT_REF_SCHEMES:
        blockers.append("external_evidence_artifact_ref_scheme_not_allowed")
    if parsed.username or parsed.password:
        blockers.append("external_evidence_artifact_ref_credentials_embedded")
    if parsed.scheme in {"http", "https"}:
        host = parsed.hostname or ""
        if not host:
            blockers.append("external_evidence_artifact_ref_host_missing")
        else:
            host_lower = host.lower()
            if host_lower in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host_lower.endswith(".local"):
                blockers.append("external_evidence_artifact_ref_local_host")
            try:
                ip = ipaddress.ip_address(host_lower)
            except ValueError:
                ip = None
            if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
                blockers.append("external_evidence_artifact_ref_private_or_reserved_ip")
    return blockers


def _parse_iso_timestamp(value: Any, field_name: str) -> tuple[datetime | None, list[str]]:
    if not isinstance(value, str) or not value.strip():
        return None, [f"external_evidence_{field_name}_missing"]
    timestamp = value.strip()
    if "T" not in timestamp:
        return None, [f"external_evidence_{field_name}_invalid"]
    normalized = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, [f"external_evidence_{field_name}_invalid"]
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, [f"external_evidence_{field_name}_timezone_missing"]
    return parsed.astimezone(timezone.utc), []


def _unexpected_fields(payload: dict[str, Any], allowed_fields: set[str]) -> list[str]:
    return sorted(str(field) for field in payload if field not in allowed_fields)


def _evidence_notes_blockers(notes: Any) -> list[str]:
    if notes is None:
        return []
    if not isinstance(notes, list):
        return ["external_evidence_notes_must_be_list"]

    blockers: list[str] = []
    if len(notes) > MAX_PRODUCTION_EVIDENCE_NOTES:
        blockers.append("external_evidence_notes_too_many")
    for note in notes:
        if not isinstance(note, str) or not note.strip():
            blockers.append("external_evidence_note_must_be_non_empty_string")
            continue
        if len(note.strip()) > MAX_PRODUCTION_EVIDENCE_NOTE_CHARS:
            blockers.append("external_evidence_note_too_long")
    return blockers


def _evidence_text_quality_blockers(
    value: Any,
    field_name: str,
    *,
    min_chars: int = 3,
    max_chars: int | None = None,
) -> list[str]:
    if not isinstance(value, str):
        return [f"external_evidence_{field_name}_missing"]
    text = value.strip()
    if not text:
        return [f"external_evidence_{field_name}_missing"]

    blockers: list[str] = []
    normalized = re.sub(r"\s+", " ", text).casefold()
    if normalized in PLACEHOLDER_EVIDENCE_VALUES:
        blockers.append(f"external_evidence_{field_name}_placeholder")
    if len(text) < min_chars:
        blockers.append(f"external_evidence_{field_name}_too_short")
    if max_chars is not None and len(text) > max_chars:
        blockers.append(f"external_evidence_{field_name}_too_long")
    return blockers


def _validate_external_evidence_item(
    item_id: str,
    item: Any,
    *,
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "id": item_id,
            "ready": False,
            "status": "missing",
            "blockers": ["external_evidence_item_missing"],
            "warnings": [],
        }

    blockers: list[str] = []
    warnings: list[str] = []
    unexpected_item_fields = _unexpected_fields(item, ALLOWED_PRODUCTION_EVIDENCE_ITEM_FIELDS)
    if unexpected_item_fields:
        blockers.append("external_evidence_unexpected_item_fields")
    status = str(item.get("status") or "")
    if status != "accepted":
        blockers.append("external_evidence_item_not_accepted")
    validated_at_utc, timestamp_blockers = _parse_iso_timestamp(item.get("validated_at"), "validated_at")
    blockers.extend(timestamp_blockers)
    if generated_at_utc is not None and validated_at_utc is not None and validated_at_utc > generated_at_utc:
        blockers.append("external_evidence_validated_at_after_generated_at")
    blockers.extend(
        _evidence_text_quality_blockers(
            item.get("validated_by"),
            "validated_by",
            max_chars=MAX_PRODUCTION_EVIDENCE_VALIDATOR_CHARS,
        )
    )
    blockers.extend(
        _evidence_text_quality_blockers(
            item.get("evidence_summary"),
            "summary",
            min_chars=MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
            max_chars=MAX_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
        )
    )
    artifact_refs = item.get("artifact_refs")
    if artifact_refs is None:
        blockers.append("external_evidence_artifact_refs_missing")
    elif not isinstance(artifact_refs, list):
        blockers.append("external_evidence_artifact_refs_must_be_list")
    elif not artifact_refs:
        blockers.append("external_evidence_artifact_refs_empty")
    else:
        if len(artifact_refs) > MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS:
            blockers.append("external_evidence_artifact_refs_too_many")
        for ref in artifact_refs:
            blockers.extend(_artifact_ref_blockers(ref))
    if item.get("secret_values_returned") is not False:
        blockers.append("external_evidence_secret_values_returned_must_be_false")

    secret_hits = _secret_pattern_hits(item)
    if secret_hits:
        blockers.append("external_evidence_secret_pattern_detected")

    return {
        "id": item_id,
        "ready": not blockers,
        "status": status or "missing",
        "blockers": blockers,
        "warnings": warnings,
        "artifact_ref_count": len(artifact_refs) if isinstance(artifact_refs, list) else 0,
        "secret_pattern_count": len(secret_hits),
        "unexpected_fields": unexpected_item_fields,
    }


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_external_evidence_file(
    production_evidence_file: Path | str | None,
    *,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    if production_evidence_file is None:
        return {
            "provided": False,
            "path": None,
            "ready": False,
            "version": None,
            "accepted_count": 0,
            "required_count": len(EXTERNAL_REQUIREMENTS),
            "blockers": [],
            "warnings": [],
            "items": [],
        }

    evidence_path = Path(production_evidence_file).resolve()
    blockers: list[str] = []
    warnings: list[str] = []
    repo_root_resolved = Path(repo_root).resolve() if repo_root is not None else None
    evidence_file_inside_repo = (
        repo_root_resolved is not None and _path_is_relative_to(evidence_path, repo_root_resolved)
    )
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "provided": True,
            "path": str(evidence_path),
            "ready": False,
            "version": None,
            "accepted_count": 0,
            "required_count": len(EXTERNAL_REQUIREMENTS),
            "blockers": ["external_evidence_file_missing"],
            "warnings": [],
            "items": [],
        }
    except json.JSONDecodeError:
        return {
            "provided": True,
            "path": str(evidence_path),
            "ready": False,
            "version": None,
            "accepted_count": 0,
            "required_count": len(EXTERNAL_REQUIREMENTS),
            "blockers": ["external_evidence_json_invalid"],
            "warnings": [],
            "items": [],
        }

    if not isinstance(payload, dict):
        return {
            "provided": True,
            "path": str(evidence_path),
            "ready": False,
            "version": None,
            "accepted_count": 0,
            "required_count": len(EXTERNAL_REQUIREMENTS),
            "blockers": ["external_evidence_root_must_be_object"],
            "warnings": [],
            "items": [],
        }

    version = payload.get("version")
    if evidence_file_inside_repo:
        blockers.append("external_evidence_file_must_be_outside_repo")
    unexpected_root_fields = _unexpected_fields(payload, ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS)
    if unexpected_root_fields:
        blockers.append("external_evidence_unexpected_root_fields")
    if version != EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION:
        blockers.append("external_evidence_version_mismatch")
    generated_at_utc, timestamp_blockers = _parse_iso_timestamp(payload.get("generated_at"), "generated_at")
    blockers.extend(timestamp_blockers)
    if payload.get("secret_values_returned") is not False:
        blockers.append("external_evidence_secret_values_returned_must_be_false")
    blockers.extend(_evidence_notes_blockers(payload.get("notes")))

    secret_hits = _secret_pattern_hits(payload)
    if secret_hits:
        blockers.append("external_evidence_secret_pattern_detected")

    required_ids = [requirement.id for requirement in EXTERNAL_REQUIREMENTS]
    items_payload = payload.get("items")
    unexpected_item_ids: list[str] = []
    if not isinstance(items_payload, dict):
        blockers.append("external_evidence_items_must_be_object")
        items_payload = {}
    else:
        unexpected_item_ids = sorted(str(item_id) for item_id in items_payload if item_id not in required_ids)
        if unexpected_item_ids:
            blockers.append("external_evidence_unexpected_item_ids")

    item_reports = [
        _validate_external_evidence_item(item_id, items_payload.get(item_id), generated_at_utc=generated_at_utc)
        for item_id in required_ids
    ]
    accepted_count = sum(1 for item in item_reports if item["ready"])
    item_blockers = [item["id"] for item in item_reports if not item["ready"]]
    if item_blockers:
        blockers.extend([f"external_evidence_item_blocked:{item_id}" for item_id in item_blockers])
    for item in item_reports:
        warnings.extend([f"{item['id']}:{warning}" for warning in item["warnings"]])

    return {
        "provided": True,
        "path": str(evidence_path),
        "ready": not blockers,
        "version": version,
        "accepted_count": accepted_count,
        "required_count": len(required_ids),
        "blockers": blockers,
        "warnings": warnings,
        "items": item_reports,
        "secret_pattern_count": len(secret_hits),
        "unexpected_fields": unexpected_root_fields,
        "unexpected_item_ids": unexpected_item_ids,
        "file_inside_repo": evidence_file_inside_repo,
        "notes_count": len(payload.get("notes")) if isinstance(payload.get("notes"), list) else 0,
    }


def build_external_acceptance_evidence_template() -> dict[str, Any]:
    """Build a pending, secret-free external production evidence skeleton."""
    return {
        "version": EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "generated_at": None,
        "secret_values_returned": False,
        "notes": list(PRODUCTION_EVIDENCE_TEMPLATE_NOTES),
        "items": {
            requirement.id: {
                "status": "pending_external_acceptance",
                "validated_at": None,
                "validated_by": None,
                "evidence_summary": "",
                "artifact_refs": [],
                "secret_values_returned": False,
            }
            for requirement in EXTERNAL_REQUIREMENTS
        },
    }


def build_production_evidence_explain(
    repo_root: Path | str,
    *,
    production_evidence_file: Path | str | None = None,
    allow_live_ready_from_evidence: bool = False,
) -> dict[str, Any]:
    """Explain what sanitized external evidence is still needed for live-order readiness."""
    report = build_completion_report(
        repo_root,
        production_evidence_file=production_evidence_file,
        allow_live_ready_from_evidence=allow_live_ready_from_evidence,
    )
    production_evidence = report["production_evidence"]
    external_status_by_id = {
        item["id"]: item
        for item in report["external_acceptance"]
    }
    evidence_item_by_id = {
        item["id"]: item
        for item in production_evidence.get("items", [])
        if isinstance(item, dict) and item.get("id")
    }

    items: list[dict[str, Any]] = []
    for requirement in EXTERNAL_REQUIREMENTS:
        evidence_item = evidence_item_by_id.get(requirement.id)
        if evidence_item is None:
            evidence_blockers = [
                "external_evidence_item_not_provided"
                if not production_evidence.get("provided")
                else "external_evidence_item_not_reported"
            ]
            evidence_ready = False
            evidence_status = "not_provided"
            artifact_ref_count = 0
            secret_pattern_count = 0
            unexpected_fields: list[str] = []
        else:
            evidence_blockers = list(evidence_item.get("blockers") or [])
            evidence_ready = bool(evidence_item.get("ready"))
            evidence_status = str(evidence_item.get("status") or "missing")
            artifact_ref_count = int(evidence_item.get("artifact_ref_count") or 0)
            secret_pattern_count = int(evidence_item.get("secret_pattern_count") or 0)
            unexpected_fields = list(evidence_item.get("unexpected_fields") or [])

        documentation_status = external_status_by_id.get(requirement.id, {}).get("status")
        items.append(
            {
                "id": requirement.id,
                "description": requirement.description,
                "documentation_status": documentation_status,
                "evidence_status": evidence_status,
                "ready": evidence_ready,
                "blockers": evidence_blockers,
                "artifact_ref_count": artifact_ref_count,
                "secret_pattern_count": secret_pattern_count,
                "unexpected_fields": unexpected_fields,
                "required_fields": list(PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS),
                "safe_artifact_ref_schemes": sorted(SAFE_ARTIFACT_REF_SCHEMES),
                "forbidden_values": list(PRODUCTION_EVIDENCE_COMMON_FORBIDDEN),
                "operator_guidance": list(PRODUCTION_EVIDENCE_ITEM_GUIDANCE.get(requirement.id, ())),
            }
        )

    return {
        "mode": "production_evidence_explain",
        "version": EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "repo_root": report["repo_root"],
        "github_upload": report["github_upload"],
        "local_v1_accepted": report["local_v1_accepted"],
        "ready_for_live_orders": report["ready_for_live_orders"],
        "production_track": report["summary"]["production_track"],
        "production_evidence": {
            "provided": production_evidence["provided"],
            "path": production_evidence["path"],
            "ready": production_evidence["ready"],
            "accepted_count": production_evidence["accepted_count"],
            "required_count": production_evidence["required_count"],
            "blockers": list(production_evidence["blockers"]),
            "warnings": list(production_evidence["warnings"]),
            "file_inside_repo": production_evidence.get("file_inside_repo", False),
        },
        "schema": {
            "allowed_root_fields": sorted(ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS),
            "allowed_item_fields": sorted(ALLOWED_PRODUCTION_EVIDENCE_ITEM_FIELDS),
            "required_item_ids": [requirement.id for requirement in EXTERNAL_REQUIREMENTS],
            "required_item_fields": list(PRODUCTION_EVIDENCE_REQUIRED_ITEM_FIELDS),
            "safe_artifact_ref_schemes": sorted(SAFE_ARTIFACT_REF_SCHEMES),
            "max_notes": MAX_PRODUCTION_EVIDENCE_NOTES,
            "max_note_chars": MAX_PRODUCTION_EVIDENCE_NOTE_CHARS,
            "max_artifact_refs_per_item": MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS,
            "max_artifact_ref_chars": MAX_PRODUCTION_EVIDENCE_ARTIFACT_REF_CHARS,
            "summary_chars": {
                "min": MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
                "max": MAX_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
            },
        },
        "items": items,
        "next_actions": [
            "Generate a repo-external skeleton with --init-production-evidence-file if no evidence file exists yet.",
            "Fill only the required schema fields after each real external acceptance is completed.",
            "Keep the filled evidence outside the code repository or in a private ops evidence location.",
            "Run --explain-production-evidence with --production-evidence-file to see item-level blockers before strict production cutover.",
            "Run --strict-production with --allow-live-ready-from-evidence only during an explicitly approved live-order cutover window.",
        ],
    }


def write_external_acceptance_evidence_template(
    output_path: Path | str,
    *,
    repo_root: Path | str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a repo-external evidence skeleton and immediately validate it."""
    root = Path(repo_root).resolve()
    destination = Path(output_path).expanduser().resolve()
    blockers: list[str] = []
    warnings: list[str] = []

    if _path_is_relative_to(destination, root):
        blockers.append("external_evidence_output_must_be_outside_repo")
    if destination.exists() and not overwrite:
        blockers.append("external_evidence_output_exists")
    if destination.suffix.lower() != ".json":
        warnings.append("external_evidence_output_should_use_json_suffix")

    if blockers:
        return {
            "created": False,
            "path": str(destination),
            "repo_root": str(root),
            "blockers": blockers,
            "warnings": warnings,
            "ready_for_live_orders": False,
        }

    payload = build_external_acceptance_evidence_template()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = _validate_external_evidence_file(destination, repo_root=root)
    return {
        "created": True,
        "path": str(destination),
        "repo_root": str(root),
        "blockers": [],
        "warnings": warnings,
        "item_ids": [requirement.id for requirement in EXTERNAL_REQUIREMENTS],
        "production_evidence_ready": validation["ready"],
        "production_evidence_blockers": validation["blockers"],
        "ready_for_live_orders": False,
        "next_actions": [
            "Fill this file only after real external acceptance is completed, then update generated_at and each accepted item.",
            "Keep the filled file outside the code repository or in a private ops evidence location.",
            "Run ai_trading_v1_completion_audit.py with --production-evidence-file against the filled file before any production cutover.",
        ],
    }


def build_completion_report(
    repo_root: Path | str,
    *,
    production_evidence_file: Path | str | None = None,
    allow_live_ready_from_evidence: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    local_items = [_evaluate_requirement(root, requirement) for requirement in LOCAL_REQUIREMENTS]
    governance_items = [_latest_memory_report(root), _git_governance_report(root)]
    external_items = [_evaluate_requirement(root, requirement) for requirement in EXTERNAL_REQUIREMENTS]
    production_evidence = _validate_external_evidence_file(production_evidence_file, repo_root=root)

    local_evidence_items = local_items + governance_items
    local_blockers = [
        item["id"]
        for item in local_evidence_items
        if item["status"] not in {"accepted"}
    ]
    missing_external_markers = [
        item["id"]
        for item in external_items
        if item["status"] in {"missing_evidence_file", "incomplete_evidence"}
    ]
    pending_external_items = [
        item["id"]
        for item in external_items
        if item["status"] in {"pending_external_acceptance", "out_of_local_v1_scope"}
    ]
    local_v1_accepted = not local_blockers and not missing_external_markers
    ready_for_live_orders = (
        local_v1_accepted
        and production_evidence["ready"]
        and allow_live_ready_from_evidence
    )
    if ready_for_live_orders:
        production_track = "accepted"
    elif production_evidence["ready"]:
        production_track = "external_evidence_accepted_pending_explicit_confirmation"
    else:
        production_track = "pending_external_acceptance"
    effective_external_pending_count = 0 if production_evidence["ready"] else len(pending_external_items)

    return {
        "local_v1_accepted": local_v1_accepted,
        "ready_for_live_orders": ready_for_live_orders,
        "github_upload": "deferred_by_user_request",
        "git_governance": next(item for item in governance_items if item["id"] == "git_governance"),
        "repo_root": str(root),
        "summary": {
            "local_track": "accepted" if not local_blockers and not missing_external_markers else "incomplete",
            "production_track": production_track,
            "external_pending_count": effective_external_pending_count,
            "documented_external_pending_count": len(pending_external_items),
            "local_blockers": local_blockers,
            "missing_external_markers": missing_external_markers,
            "production_evidence_blockers": list(production_evidence["blockers"]),
        },
        "local_evidence": local_evidence_items,
        "external_acceptance": external_items,
        "production_evidence": production_evidence,
        "next_actions": [
            "Continue local development only on codex/ai-agent-multitenant-foundation; do not push or merge while GitHub upload is skipped.",
            "For production live-order acceptance, provide real Auth/JWKS, real order-backend URL/token, hard-risk values, and explicit production handoff approval.",
            "For real model-adjust acceptance, configure a user's Hyper AI DeepSeek/Qwen profile and run the live model-adjust runner with explicit confirmation.",
            "Record external acceptance in a sanitized production evidence JSON file outside the code repository with documented schema fields/item IDs, bounded notes, bounded non-placeholder validated_by and evidence_summary, ISO timestamps, and bounded safe artifact refs; do not include API keys, bearer tokens, DB URLs, private keys, or raw authorization headers.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root to audit. Defaults to this script's repository.",
    )
    parser.add_argument("--strict-local", action="store_true", help="Exit 1 unless local V1 evidence is accepted.")
    parser.add_argument(
        "--strict-production",
        action="store_true",
        help="Exit 1 unless production/live-order acceptance has no pending external items.",
    )
    parser.add_argument(
        "--production-evidence-file",
        help="Optional sanitized JSON file with real external production acceptance evidence.",
    )
    parser.add_argument(
        "--allow-live-ready-from-evidence",
        action="store_true",
        help=(
            "Allow ready_for_live_orders=true when local V1 and the production evidence file are both accepted. "
            "Without this explicit flag, accepted evidence is reported but live-order readiness remains false."
        ),
    )
    parser.add_argument(
        "--init-production-evidence-file",
        help=(
            "Create a pending external production evidence skeleton at this path and exit. "
            "The output path must be outside the code repository unless you are editing the checked-in template manually."
        ),
    )
    parser.add_argument(
        "--overwrite-production-evidence-file",
        action="store_true",
        help="Allow --init-production-evidence-file to replace an existing output file.",
    )
    parser.add_argument(
        "--explain-production-evidence",
        action="store_true",
        help="Print a non-secret item-level checklist for the external production evidence file.",
    )
    args = parser.parse_args()

    if args.init_production_evidence_file:
        init_report = write_external_acceptance_evidence_template(
            args.init_production_evidence_file,
            repo_root=args.repo_root,
            overwrite=args.overwrite_production_evidence_file,
        )
        print(json.dumps(init_report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if init_report["created"] else 1

    if args.explain_production_evidence:
        explain_report = build_production_evidence_explain(
            args.repo_root,
            production_evidence_file=args.production_evidence_file,
            allow_live_ready_from_evidence=args.allow_live_ready_from_evidence,
        )
        print(json.dumps(explain_report, ensure_ascii=False, indent=2, sort_keys=True))
        if args.strict_local and not explain_report["local_v1_accepted"]:
            return 1
        if args.strict_production and not explain_report["ready_for_live_orders"]:
            return 1
        return 0

    report = build_completion_report(
        args.repo_root,
        production_evidence_file=args.production_evidence_file,
        allow_live_ready_from_evidence=args.allow_live_ready_from_evidence,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.strict_local and not report["local_v1_accepted"]:
        return 1
    if args.strict_production and not report["ready_for_live_orders"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
