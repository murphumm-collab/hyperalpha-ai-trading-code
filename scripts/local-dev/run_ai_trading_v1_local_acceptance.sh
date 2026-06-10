#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIRM_LOCAL_MOCK_HANDOFF=false

usage() {
  cat <<'EOF'
Usage:
  scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff

Runs the AI Trading V1 local acceptance gate:
  - backend compile check
  - AI Trading pytest regression
  - API-level V1 smoke runner
  - live DeepSeek/Qwen model-adjust runner must stay blocked without explicit confirmation
  - default production handoff gate must stay blocked
  - default production readiness gate must stay blocked
  - default production readiness DB-audit gate must stay blocked
  - local V1 completion boundary audit must pass
  - local completion summary gate must confirm local accepted, live orders false, and Git governance accepted
  - production completion boundary audit must stay blocked
  - production evidence initializer gate must create repo-external pending evidence and keep live orders false
  - production evidence template must stay blocked
  - frontend production build
  - local LaunchAgent runtime mirror sync
  - local runtime readiness check
  - live LaunchAgent/mock-gateway handoff acceptance

The confirmation flag is required because the final step submits one signal to
the local mock gateway and creates local audit records. The live-stack runner
still refuses non-local URLs and requires runtime gateway target_kind=local_mock.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm-local-mock-handoff)
      CONFIRM_LOCAL_MOCK_HANDOFF=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$CONFIRM_LOCAL_MOCK_HANDOFF" != "true" ]]; then
  echo "Refusing to run without --confirm-local-mock-handoff." >&2
  echo "This protects against accidental signal handoff, even to the local mock gateway." >&2
  usage >&2
  exit 2
fi

run_step() {
  local name="$1"
  shift
  echo
  echo "==> $name"
  "$@"
}

run_expected_failure() {
  local name="$1"
  shift
  echo
  echo "==> $name"
  set +e
  "$@"
  local rc=$?
  set -e
  if [[ "$rc" -ne 1 ]]; then
    echo "Expected exit status 1, got $rc" >&2
    return 1
  fi
  echo "Expected blocker confirmed with exit status 1"
}

run_local_completion_summary_gate() {
  local report_file
  report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-completion-audit.XXXXXX.json")"
  (
    cd backend
    uv run python scripts/ai_trading_v1_completion_audit.py --strict-local > "$report_file"
  )
  cat "$report_file"
  python3 - "$report_file" <<'PY'
import json
import sys

expected_branch = "codex/ai-agent-multitenant-foundation"
report_path = sys.argv[1]
with open(report_path, encoding="utf-8") as handle:
    report = json.load(handle)

git_governance = report.get("git_governance") or {}
summary = report.get("summary") or {}
checks = {
    "local_v1_accepted": report.get("local_v1_accepted") is True,
    "ready_for_live_orders_false": report.get("ready_for_live_orders") is False,
    "github_upload_deferred": report.get("github_upload") == "deferred_by_user_request",
    "git_governance.status": git_governance.get("status") == "accepted",
    "git_governance.current_branch": git_governance.get("current_branch") == expected_branch,
    "local_blockers_empty": summary.get("local_blockers") == [],
    "production_track_pending": summary.get("production_track") == "pending_external_acceptance",
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "local_completion_summary_gate": "accepted" if not failed else "failed",
    "checked": checks,
    "current_branch": git_governance.get("current_branch"),
    "github_upload": report.get("github_upload"),
    "ready_for_live_orders": report.get("ready_for_live_orders"),
}, ensure_ascii=False, indent=2, sort_keys=True))
if failed:
    raise SystemExit("Local completion summary gate failed: " + ", ".join(failed))
PY
  rm -f "$report_file"
}

run_production_evidence_initializer_gate() {
  local evidence_file
  local init_report_file
  local audit_report_file
  evidence_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence.XXXXXX.json")"
  init_report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence-init.XXXXXX.json")"
  audit_report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence-audit.XXXXXX.json")"
  rm -f "$evidence_file"

  (
    cd backend
    uv run python scripts/ai_trading_v1_completion_audit.py \
      --init-production-evidence-file "$evidence_file" > "$init_report_file"
  )
  cat "$init_report_file"
  python3 - "$init_report_file" <<'PY'
import json
import sys

expected_item_ids = {
    "macos_reboot_recovery",
    "real_model_profile_live_acceptance",
    "real_order_backend_handoff",
    "production_auth_hard_risk_readiness",
    "admin_readiness_real_auth_visual",
    "production_agent_session_visual",
    "real_exchange_execution",
}
with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

checks = {
    "created": report.get("created") is True,
    "blockers_empty": report.get("blockers") == [],
    "production_evidence_ready_false": report.get("production_evidence_ready") is False,
    "ready_for_live_orders_false": report.get("ready_for_live_orders") is False,
    "item_ids_exact": set(report.get("item_ids") or []) == expected_item_ids,
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "production_evidence_initializer_gate": "initialized" if not failed else "failed",
    "checked": checks,
    "path": report.get("path"),
    "production_evidence_blockers": report.get("production_evidence_blockers"),
}, ensure_ascii=False, indent=2, sort_keys=True))
if failed:
    raise SystemExit("Production evidence initializer gate failed: " + ", ".join(failed))
PY

  set +e
  (
    cd backend
    uv run python scripts/ai_trading_v1_completion_audit.py \
      --production-evidence-file "$evidence_file" \
      --strict-production > "$audit_report_file"
  )
  local rc=$?
  set -e
  cat "$audit_report_file"
  if [[ "$rc" -ne 1 ]]; then
    echo "Expected initialized production evidence to keep strict-production blocked, got $rc" >&2
    return 1
  fi
  python3 - "$audit_report_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)
production_evidence = report.get("production_evidence") or {}
blockers = production_evidence.get("blockers") or []
checks = {
    "production_evidence_provided": production_evidence.get("provided") is True,
    "production_evidence_ready_false": production_evidence.get("ready") is False,
    "repo_external": production_evidence.get("file_inside_repo") is False,
    "ready_for_live_orders_false": report.get("ready_for_live_orders") is False,
    "accepted_count_zero": production_evidence.get("accepted_count") == 0,
    "generated_at_missing_blocker": "external_evidence_generated_at_missing" in blockers,
    "real_order_backend_blocked": "external_evidence_item_blocked:real_order_backend_handoff" in blockers,
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "production_evidence_initializer_strict_production_gate": "blocked_as_expected" if not failed else "failed",
    "checked": checks,
    "ready_for_live_orders": report.get("ready_for_live_orders"),
}, ensure_ascii=False, indent=2, sort_keys=True))
if failed:
    raise SystemExit("Initialized evidence strict-production gate failed: " + ", ".join(failed))
PY

  rm -f "$evidence_file" "$init_report_file" "$audit_report_file"
}

run_runtime_readiness_with_retry() {
  local attempts=12
  local delay_seconds=5
  local attempt

  for attempt in $(seq 1 "$attempts"); do
    echo "Runtime readiness attempt $attempt/$attempts"
    if (
      cd backend
      uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current
    ); then
      return 0
    fi
    if [[ "$attempt" -lt "$attempts" ]]; then
      echo "Runtime not ready after LaunchAgent sync; waiting ${delay_seconds}s before retry..."
      sleep "$delay_seconds"
    fi
  done

  echo "Runtime readiness failed after $attempts attempts" >&2
  return 1
}

cd "$REPO_ROOT"

run_step "Backend compile check" \
  bash -lc "cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_production_handoff_service.py services/ai_trading_production_readiness_service.py database/migrations/add_ai_trading_agent_session_fields.py scripts/ai_trading_v1_live_stack_acceptance.py scripts/ai_trading_v1_acceptance_smoke.py scripts/ai_trading_model_adjust_live_acceptance.py scripts/ai_trading_v1_env_check.py scripts/ai_trading_production_handoff_check.py scripts/ai_trading_v1_production_readiness_check.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py"

run_step "AI Trading backend regression" \
  bash -lc "cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q"

run_step "API-level V1 smoke" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_acceptance_smoke.py"

run_expected_failure "Live model-adjust runner refuses without confirmation" \
  bash -lc "cd backend && uv run python scripts/ai_trading_model_adjust_live_acceptance.py"

run_expected_failure "Default production handoff gate remains blocked" \
  bash -lc "cd backend && env -u AI_TRADING_SIGNAL_GATEWAY_ENABLED -u AI_TRADING_SIGNAL_GATEWAY_URL -u AI_TRADING_SIGNAL_GATEWAY_TOKEN -u AI_TRADING_PRODUCTION_HANDOFF_APPROVED uv run python scripts/ai_trading_production_handoff_check.py --strict"

run_expected_failure "Default production readiness gate remains blocked" \
  bash -lc "cd backend && env -u AUTH_REQUIRE_VERIFIED_BEARER -u AUTH_JWKS_URL -u AUTH_JWT_ISSUER -u AUTH_JWT_AUDIENCE -u AUTH_JWT_ALGORITHMS -u AUTH_ADMIN_USERNAMES -u AI_TRADING_SIGNAL_GATEWAY_ENABLED -u AI_TRADING_SIGNAL_GATEWAY_URL -u AI_TRADING_SIGNAL_GATEWAY_TOKEN -u AI_TRADING_PRODUCTION_HANDOFF_APPROVED -u AI_HARD_MAX_ORDER_NOTIONAL_USD -u AI_HARD_REQUIRE_STOP_LOSS -u AI_HARD_REQUIRE_TAKE_PROFIT uv run python scripts/ai_trading_v1_production_readiness_check.py --strict"

run_expected_failure "Default production readiness DB-audit gate remains blocked" \
  bash -lc "cd backend && env -u AUTH_REQUIRE_VERIFIED_BEARER -u AUTH_JWKS_URL -u AUTH_JWT_ISSUER -u AUTH_JWT_AUDIENCE -u AUTH_JWT_ALGORITHMS -u AUTH_ADMIN_USERNAMES -u AI_TRADING_SIGNAL_GATEWAY_ENABLED -u AI_TRADING_SIGNAL_GATEWAY_URL -u AI_TRADING_SIGNAL_GATEWAY_TOKEN -u AI_TRADING_PRODUCTION_HANDOFF_APPROVED -u AI_HARD_MAX_ORDER_NOTIONAL_USD -u AI_HARD_REQUIRE_STOP_LOSS -u AI_HARD_REQUIRE_TAKE_PROFIT uv run python scripts/ai_trading_v1_production_readiness_check.py --strict --include-db-audits"

run_step "Local V1 completion boundary audit" \
  run_local_completion_summary_gate

run_expected_failure "Production completion boundary audit remains blocked" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-production"

run_step "Production evidence initializer gate" \
  run_production_evidence_initializer_gate

run_expected_failure "Production evidence template remains blocked" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production"

run_step "Frontend build" \
  bash -lc "cd frontend && npm run build"

run_step "Local LaunchAgent runtime sync" \
  bash -lc "scripts/local-dev/install_launch_agent.sh"

run_step "Local runtime readiness" \
  run_runtime_readiness_with_retry

run_step "Live local mock handoff acceptance" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff"

echo
echo "AI Trading V1 local acceptance completed."
