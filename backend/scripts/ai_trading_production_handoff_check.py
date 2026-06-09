"""Check production readiness for AI Trading signal handoff.

This script does not submit signals or contact the order backend. It verifies
that handoff configuration is explicitly production-like before a live order
backend acceptance run.

Run from backend:

    uv run python scripts/ai_trading_production_handoff_check.py --strict

Use --env-file to evaluate a deployment env file without printing secrets.
"""

from __future__ import annotations

import argparse
import json

from services.ai_trading_production_handoff_service import (
    APPROVAL_ENV,
    _parse_env_file,
    build_report,
    load_env as _load_env,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="Optional .env-style file to evaluate.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when production handoff is not ready.")
    parser.add_argument(
        "--allow-missing-approval-flag",
        action="store_true",
        help=f"Do not require {APPROVAL_ENV}=true. Intended only for exploratory dry runs.",
    )
    args = parser.parse_args()

    report = build_report(
        _load_env(args.env_file),
        require_approval_flag=not args.allow_missing_approval_flag,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and not report["production_handoff_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
