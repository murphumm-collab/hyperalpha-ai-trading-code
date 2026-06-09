"""Check AI Trading V1 production readiness without network calls or submissions.

This aggregates the no-network checks that must pass before a production-like
order-backend handoff acceptance window. It never prints secret values.

Run from backend:

    uv run python scripts/ai_trading_v1_production_readiness_check.py --strict

Use --env-file to evaluate a deployment env file without loading secrets into
the shell output.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Mapping, Optional

from services.ai_trading_production_readiness_service import (
    build_agent_session_context_audit_report,
    build_handoff_attempt_audit_report,
    build_report,
    load_env as _load_env,
)


def _db_audit_unavailable_report(base_report: Mapping[str, Any], error_type: str) -> dict[str, Any]:
    report = {
        "production_ready": False,
        "blockers": list(base_report.get("blockers") or []),
        "warnings": list(base_report.get("warnings") or []),
        "checks": dict(base_report.get("checks") or {}),
        "next_actions": list(base_report.get("next_actions") or []),
    }
    report["blockers"].append("db_audit:db_audit_unavailable")
    report["checks"]["db_audit"] = {
        "ready": False,
        "blockers": ["db_audit_unavailable"],
        "warnings": [],
        "checks": {
            "error_type": error_type,
            "secret_values_returned": False,
        },
    }
    report["next_actions"].append(
        "Fix AI Trading production readiness DB audit connectivity before production acceptance; "
        "the CLI does not print database URLs, credentials, or exception text."
    )
    return report


def build_readiness_report(
    env: Mapping[str, str],
    *,
    include_db_audits: bool = False,
    require_handoff_approval_flag: bool = True,
    session_factory: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    if not include_db_audits:
        return build_report(
            env,
            require_handoff_approval_flag=require_handoff_approval_flag,
        )

    try:
        if session_factory is None:
            from database.connection import SessionLocal

            session_factory = SessionLocal
        db = session_factory()
        try:
            return build_report(
                env,
                require_handoff_approval_flag=require_handoff_approval_flag,
                handoff_attempt_audit_report=build_handoff_attempt_audit_report(db),
                agent_session_context_audit_report=build_agent_session_context_audit_report(db),
            )
        finally:
            db.close()
    except Exception as exc:
        base_report = build_report(
            env,
            require_handoff_approval_flag=require_handoff_approval_flag,
        )
        return _db_audit_unavailable_report(base_report, exc.__class__.__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="Optional .env-style file to evaluate.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when production readiness blockers exist.")
    parser.add_argument(
        "--include-db-audits",
        action="store_true",
        help=(
            "Include persisted handoff-attempt and agent-session context audits. "
            "This opens a local DB session but still performs no network calls or submissions."
        ),
    )
    parser.add_argument(
        "--allow-missing-handoff-approval-flag",
        action="store_true",
        help="Do not require AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true. Intended only for exploratory dry runs.",
    )
    args = parser.parse_args()

    report = build_readiness_report(
        _load_env(args.env_file),
        include_db_audits=args.include_db_audits,
        require_handoff_approval_flag=not args.allow_missing_handoff_approval_flag,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and not report["production_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
