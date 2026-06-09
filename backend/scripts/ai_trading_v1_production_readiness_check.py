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

from services.ai_trading_production_readiness_service import (
    build_report,
    load_env as _load_env,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="Optional .env-style file to evaluate.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when production readiness blockers exist.")
    parser.add_argument(
        "--allow-missing-handoff-approval-flag",
        action="store_true",
        help="Do not require AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true. Intended only for exploratory dry runs.",
    )
    args = parser.parse_args()

    report = build_report(
        _load_env(args.env_file),
        require_handoff_approval_flag=not args.allow_missing_handoff_approval_flag,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and not report["production_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
