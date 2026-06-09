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
  - frontend production build
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

cd "$REPO_ROOT"

run_step "Backend compile check" \
  bash -lc "cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_production_handoff_service.py services/ai_trading_production_readiness_service.py database/migrations/add_ai_trading_agent_session_fields.py scripts/ai_trading_v1_live_stack_acceptance.py scripts/ai_trading_v1_acceptance_smoke.py scripts/ai_trading_model_adjust_live_acceptance.py scripts/ai_trading_v1_env_check.py scripts/ai_trading_production_handoff_check.py scripts/ai_trading_v1_production_readiness_check.py tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py"

run_step "AI Trading backend regression" \
  bash -lc "cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q"

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

run_step "Frontend build" \
  bash -lc "cd frontend && npm run build"

run_step "Local runtime readiness" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict"

run_step "Live local mock handoff acceptance" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff"

echo
echo "AI Trading V1 local acceptance completed."
