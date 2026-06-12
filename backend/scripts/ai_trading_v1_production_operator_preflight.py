"""Aggregate AI Trading production operator preflight checks.

This command is intentionally read-only. It does not call models, exchanges,
GitHub, or order backends. It combines the existing local runtime check,
production readiness check, completion audit, and Git governance status into
one non-secret report an operator can run before a real live-order cutover.

Run from backend:

    uv run python scripts/ai_trading_v1_production_operator_preflight.py --strict

Without real production env values and an accepted external evidence file,
--strict is expected to exit 1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

import ai_trading_v1_completion_audit as completion_audit
import ai_trading_v1_env_check as env_check
import ai_trading_v1_production_readiness_check as production_readiness_check


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_BRANCH = completion_audit.EXPECTED_LOCAL_DEVELOPMENT_BRANCH
REDACTED_SENSITIVE_PREFLIGHT_VALUE = "[redacted_sensitive_preflight_value]"


def _run_git(repo_root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_report(repo_root: Path) -> dict[str, Any]:
    branch = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run_git(repo_root, ["rev-parse", "HEAD"])
    porcelain = _run_git(repo_root, ["status", "--porcelain"])
    dirty_entries = [line for line in (porcelain or "").splitlines() if line.strip()]
    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if branch is None:
        blockers.append("git_metadata_unavailable")
    elif branch == "HEAD":
        blockers.append("detached_head")
    elif branch != EXPECTED_BRANCH:
        blockers.append("unexpected_branch")
    if dirty_entries:
        blockers.append("working_tree_has_uncommitted_changes")
        warnings.append("working_tree_has_uncommitted_changes")
        next_actions.append(
            "Commit or discard local source changes before production operator preflight; "
            "dirty worktrees cannot be used for live-order cutover acceptance."
        )

    return {
        "expected_branch": EXPECTED_BRANCH,
        "current_branch": branch,
        "head_commit": commit,
        "branch_ready": not blockers,
        "dirty": bool(dirty_entries),
        "dirty_entry_count": len(dirty_entries),
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": next_actions,
        "github_upload": "deferred_by_user_request",
        "secret_policy": "metadata_only_no_remote_or_credentials",
    }


def _dedupe(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _prefixed(component: str, values: Iterable[str]) -> list[str]:
    return [f"{component}:{value}" for value in values if isinstance(value, str) and value]


def _redact_secret_like_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_secret_like_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_secret_like_values(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_secret_like_values(item) for item in value]
    if isinstance(value, str) and completion_audit._secret_pattern_hits(value):
        return REDACTED_SENSITIVE_PREFLIGHT_VALUE
    return value


def _local_runtime_report(
    *,
    frontend_url: str,
    backend_url: str,
    mock_gateway_url: str,
    repo_root: Path,
    runtime_root: Path,
    require_runtime_mirror_current: bool,
    skip_local_runtime: bool,
) -> dict[str, Any]:
    if skip_local_runtime:
        return {
            "skipped": True,
            "ready": None,
            "blockers": [],
            "next_actions": [
                "Local runtime probe skipped; run without --skip-local-runtime when verifying this machine's LaunchAgent/runtime mirror."
            ],
            "secret_policy": "skipped_no_probe",
        }
    return {
        "skipped": False,
        **env_check.build_report(
            frontend_url=frontend_url,
            backend_url=backend_url,
            mock_gateway_url=mock_gateway_url,
            repo_root=repo_root,
            runtime_root=runtime_root,
            require_runtime_mirror_current=require_runtime_mirror_current,
        ),
    }


def build_operator_preflight_report(
    *,
    repo_root: Path | str = DEFAULT_REPO_ROOT,
    env_file: str | None = None,
    production_evidence_file: str | None = None,
    allow_live_ready_from_evidence: bool = False,
    include_db_audits: bool = False,
    allow_missing_handoff_approval_flag: bool = False,
    frontend_url: str = "http://127.0.0.1:5174/app/ai-trading",
    backend_url: str = "http://127.0.0.1:8802",
    mock_gateway_url: str = "http://127.0.0.1:5621",
    runtime_root: Path | str = env_check.DEFAULT_RUNTIME_ROOT,
    require_runtime_mirror_current: bool = True,
    skip_local_runtime: bool = False,
    require_local_runtime: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    runtime_root_path = Path(runtime_root).expanduser().resolve()
    local_runtime = _local_runtime_report(
        frontend_url=frontend_url,
        backend_url=backend_url,
        mock_gateway_url=mock_gateway_url,
        repo_root=root,
        runtime_root=runtime_root_path,
        require_runtime_mirror_current=require_runtime_mirror_current,
        skip_local_runtime=skip_local_runtime,
    )
    production_readiness = production_readiness_check.build_readiness_report(
        production_readiness_check._load_env(env_file),
        include_db_audits=include_db_audits,
        require_handoff_approval_flag=not allow_missing_handoff_approval_flag,
    )
    completion = completion_audit.build_completion_report(
        root,
        production_evidence_file=production_evidence_file,
        allow_live_ready_from_evidence=allow_live_ready_from_evidence,
    )
    git = _git_report(root)

    blockers: list[str] = []
    warnings: list[str] = []
    if not git["branch_ready"]:
        blockers.extend(_prefixed("git", git["blockers"]))
    warnings.extend(_prefixed("git", git["warnings"]))
    if not completion.get("local_v1_accepted"):
        blockers.append("completion:local_v1_not_accepted")
    if not completion.get("ready_for_live_orders"):
        blockers.append("completion:live_orders_not_ready")
    if not production_readiness.get("production_ready"):
        blockers.append("production_readiness:not_ready")
        blockers.extend(_prefixed("production_readiness", production_readiness.get("blockers") or []))
    if require_local_runtime and not local_runtime.get("ready"):
        blockers.append("local_runtime:not_ready")
        blockers.extend(_prefixed("local_runtime", local_runtime.get("blockers") or []))

    next_actions = _dedupe(
        [
            *(git.get("next_actions") or []),
            *(completion.get("next_actions") or []),
            *(production_readiness.get("next_actions") or []),
            *(local_runtime.get("next_actions") or []),
            "Run this preflight again with --production-evidence-file <external-json> after real external acceptance is recorded outside the repository.",
        ]
    )
    preflight_ready = not blockers

    report = {
        "mode": "ai_trading_production_operator_preflight",
        "preflight_ready": preflight_ready,
        "ready_for_live_orders": completion.get("ready_for_live_orders") is True,
        "secret_policy": (
            "no_model_calls_no_exchange_calls_no_order_backend_calls_no_github_calls_"
            "no_env_secret_values_returned"
        ),
        "summary": {
            "git_branch_ready": git["branch_ready"],
            "git_current_branch": git["current_branch"],
            "git_dirty": git["dirty"],
            "local_runtime_checked": not skip_local_runtime,
            "local_runtime_required": require_local_runtime,
            "local_runtime_ready": local_runtime.get("ready"),
            "local_v1_accepted": completion.get("local_v1_accepted"),
            "production_ready": production_readiness.get("production_ready"),
            "production_evidence_ready": (completion.get("production_evidence") or {}).get("ready"),
            "production_track": (completion.get("summary") or {}).get("production_track"),
            "external_pending_count": (completion.get("summary") or {}).get("external_pending_count"),
            "github_upload": completion.get("github_upload"),
        },
        "blockers": _dedupe(blockers),
        "warnings": _dedupe(warnings + list(production_readiness.get("warnings") or [])),
        "next_actions": next_actions,
        "components": {
            "git": git,
            "local_runtime": local_runtime,
            "production_readiness": production_readiness,
            "completion": completion,
        },
    }
    return _redact_secret_like_values(report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--env-file", help="Optional production .env-style file to evaluate without printing secrets.")
    parser.add_argument("--production-evidence-file", help="Optional external sanitized production evidence JSON file.")
    parser.add_argument(
        "--allow-live-ready-from-evidence",
        action="store_true",
        help="Allow completion audit to mark live orders ready when accepted external evidence is supplied.",
    )
    parser.add_argument("--include-db-audits", action="store_true", help="Include local DB handoff/session audits.")
    parser.add_argument(
        "--allow-missing-handoff-approval-flag",
        action="store_true",
        help="Do not require AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true in readiness checks.",
    )
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5174/app/ai-trading")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8802")
    parser.add_argument("--mock-gateway-url", default="http://127.0.0.1:5621")
    parser.add_argument("--runtime-root", default=str(env_check.DEFAULT_RUNTIME_ROOT))
    parser.add_argument(
        "--skip-local-runtime",
        action="store_true",
        help="Skip localhost runtime probes; useful when running against a deployment env file from CI/ops.",
    )
    parser.add_argument(
        "--require-local-runtime",
        action="store_true",
        help="Treat local runtime readiness as a preflight blocker.",
    )
    parser.add_argument(
        "--allow-stale-runtime-mirror",
        action="store_true",
        help="Do not require the LaunchAgent runtime mirror metadata to match the current source tree.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 unless the preflight is ready for cutover.")
    args = parser.parse_args()

    report = build_operator_preflight_report(
        repo_root=args.repo_root,
        env_file=args.env_file,
        production_evidence_file=args.production_evidence_file,
        allow_live_ready_from_evidence=args.allow_live_ready_from_evidence,
        include_db_audits=args.include_db_audits,
        allow_missing_handoff_approval_flag=args.allow_missing_handoff_approval_flag,
        frontend_url=args.frontend_url,
        backend_url=args.backend_url,
        mock_gateway_url=args.mock_gateway_url,
        runtime_root=args.runtime_root,
        require_runtime_mirror_current=not args.allow_stale_runtime_mirror,
        skip_local_runtime=args.skip_local_runtime,
        require_local_runtime=args.require_local_runtime,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and not report["preflight_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
