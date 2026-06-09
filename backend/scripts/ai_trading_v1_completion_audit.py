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
            "ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff",
            "Production evidence template remains blocked",
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
        description="Feature status marks the local aggregate DB-audit readiness gate as accepted and remote push as skipped.",
        path="docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md",
        required_phrases=(
            "Local V1 Production Evidence Gate Accepted / Remote Push Skipped",
            "| AI Trading aggregate acceptance DB-audit gate | Done |",
            "| AI Trading V1 completion boundary audit | Done |",
            "| AI Trading production evidence gate | Done |",
            "| AI Trading production evidence text quality | Done |",
            "| AI Trading production evidence item IDs | Done |",
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


def _evidence_text_quality_blockers(
    value: Any,
    field_name: str,
    *,
    min_chars: int = 3,
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
    blockers.extend(_evidence_text_quality_blockers(item.get("validated_by"), "validated_by"))
    blockers.extend(
        _evidence_text_quality_blockers(
            item.get("evidence_summary"),
            "summary",
            min_chars=MIN_PRODUCTION_EVIDENCE_SUMMARY_CHARS,
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


def _validate_external_evidence_file(production_evidence_file: Path | str | None) -> dict[str, Any]:
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
    unexpected_root_fields = _unexpected_fields(payload, ALLOWED_PRODUCTION_EVIDENCE_ROOT_FIELDS)
    if unexpected_root_fields:
        blockers.append("external_evidence_unexpected_root_fields")
    if version != EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION:
        blockers.append("external_evidence_version_mismatch")
    generated_at_utc, timestamp_blockers = _parse_iso_timestamp(payload.get("generated_at"), "generated_at")
    blockers.extend(timestamp_blockers)
    if payload.get("secret_values_returned") is not False:
        blockers.append("external_evidence_secret_values_returned_must_be_false")

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
    }


def build_completion_report(
    repo_root: Path | str,
    *,
    production_evidence_file: Path | str | None = None,
    allow_live_ready_from_evidence: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    local_items = [_evaluate_requirement(root, requirement) for requirement in LOCAL_REQUIREMENTS]
    governance_items = [_latest_memory_report(root)]
    external_items = [_evaluate_requirement(root, requirement) for requirement in EXTERNAL_REQUIREMENTS]
    production_evidence = _validate_external_evidence_file(production_evidence_file)

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
            "Record external acceptance in a sanitized production evidence JSON file with documented schema fields/item IDs, non-placeholder validated_by and evidence_summary, ISO timestamps, and safe artifact refs; do not include API keys, bearer tokens, DB URLs, private keys, or raw authorization headers.",
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
    args = parser.parse_args()

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
