"""Audit AI Trading V1 completion boundaries from local evidence.

This script does not call models, exchanges, GitHub, or order backends. It reads
the checked-in acceptance/status/memory documents and reports whether the local
V1 track is accepted, while keeping production/live-order work explicitly
pending until real external evidence exists.

Run from backend:

    uv run python scripts/ai_trading_v1_completion_audit.py --strict-local

Use --strict-production only for a production cutover audit; it intentionally
fails while real Auth/JWKS, model keys, order backend, and live execution remain
unverified.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
            "Local V1 Completion Boundary Audit Accepted / Remote Push Skipped",
            "| AI Trading aggregate acceptance DB-audit gate | Done |",
            "| AI Trading V1 completion boundary audit | Done |",
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


def build_completion_report(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    local_items = [_evaluate_requirement(root, requirement) for requirement in LOCAL_REQUIREMENTS]
    governance_items = [_latest_memory_report(root)]
    external_items = [_evaluate_requirement(root, requirement) for requirement in EXTERNAL_REQUIREMENTS]

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

    return {
        "local_v1_accepted": not local_blockers and not missing_external_markers,
        "ready_for_live_orders": False,
        "github_upload": "deferred_by_user_request",
        "repo_root": str(root),
        "summary": {
            "local_track": "accepted" if not local_blockers and not missing_external_markers else "incomplete",
            "production_track": "pending_external_acceptance",
            "external_pending_count": len(pending_external_items),
            "local_blockers": local_blockers,
            "missing_external_markers": missing_external_markers,
        },
        "local_evidence": local_evidence_items,
        "external_acceptance": external_items,
        "next_actions": [
            "Continue local development only on codex/ai-agent-multitenant-foundation; do not push or merge while GitHub upload is skipped.",
            "For production live-order acceptance, provide real Auth/JWKS, real order-backend URL/token, hard-risk values, and explicit production handoff approval.",
            "For real model-adjust acceptance, configure a user's Hyper AI DeepSeek/Qwen profile and run the live model-adjust runner with explicit confirmation.",
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
    args = parser.parse_args()

    report = build_completion_report(args.repo_root)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.strict_local and not report["local_v1_accepted"]:
        return 1
    if args.strict_production and not report["ready_for_live_orders"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
