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
  - default production operator preflight must stay blocked
  - local V1 completion boundary audit must pass
  - local completion summary gate must confirm local accepted, live orders false, and Git governance accepted
  - production completion boundary audit must stay blocked
  - production evidence explain mode gate must report item-level blockers without unlocking live orders
  - production evidence initializer gate must create repo-external pending evidence and keep live orders false
  - production evidence template must stay blocked
  - frontend production build
  - local LaunchAgent runtime mirror sync
  - local runtime readiness check
  - transient local fork/spawn retry for resource-pressure failures
  - live LaunchAgent/mock-gateway handoff acceptance

The confirmation flag is required because the final step submits one signal to
the local mock gateway and creates local audit records. The live-stack runner
still refuses non-local URLs and requires runtime gateway target_kind=local_mock.

Transient local runner retries can be tuned with:
  AI_TRADING_TRANSIENT_RETRY_ATTEMPTS (default 3)
  AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS (default 5)
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

positive_int_or_default() {
  local value="$1"
  local fallback="$2"

  if [[ -z "$value" || "$value" =~ [^0-9] || "$value" -lt 1 ]]; then
    printf '%s\n' "$fallback"
  else
    printf '%s\n' "$value"
  fi
}

transient_retry_attempts() {
  positive_int_or_default "${AI_TRADING_TRANSIENT_RETRY_ATTEMPTS:-}" 3
}

transient_retry_sleep_seconds() {
  positive_int_or_default "${AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS:-}" 5
}

is_transient_resource_failure() {
  local rc="$1"
  local output_file="$2"
  local line

  [[ "$rc" -eq 2 || "$rc" -eq 128 ]] || return 1

  while IFS= read -r line; do
    case "$line" in
      *"Resource temporarily unavailable"*|*"Failed to spawn"*|*"fork failed"*)
        return 0
        ;;
    esac
  done < "$output_file"

  return 1
}

run_command_with_transient_retry() {
  local name="$1"
  shift
  local attempts
  local delay_seconds
  local attempt
  local output_file
  local rc

  attempts="$(transient_retry_attempts)"
  delay_seconds="$(transient_retry_sleep_seconds)"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    output_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-local-step.log.XXXXXX")"
    set +e
    "$@" > "$output_file" 2>&1
    rc=$?
    set -e
    cat "$output_file"

    if [[ "$rc" -eq 0 ]]; then
      rm -f "$output_file"
      return 0
    fi

    if is_transient_resource_failure "$rc" "$output_file" && [[ "$attempt" -lt "$attempts" ]]; then
      echo "Transient local resource failure during $name (exit $rc); retrying in ${delay_seconds}s ($attempt/$attempts)..." >&2
      rm -f "$output_file"
      sleep "$delay_seconds"
      continue
    fi

    rm -f "$output_file"
    return "$rc"
  done
}

run_step() {
  local name="$1"
  shift
  echo
  echo "==> $name"
  run_command_with_transient_retry "$name" "$@"
}

run_expected_failure() {
  local name="$1"
  shift
  local attempts
  local delay_seconds
  local attempt
  local output_file
  local rc

  echo
  echo "==> $name"

  attempts="$(transient_retry_attempts)"
  delay_seconds="$(transient_retry_sleep_seconds)"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    output_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-local-expected-failure.log.XXXXXX")"
    set +e
    "$@" > "$output_file" 2>&1
    rc=$?
    set -e
    cat "$output_file"

    if [[ "$rc" -eq 1 ]]; then
      rm -f "$output_file"
      echo "Expected blocker confirmed with exit status 1"
      return 0
    fi

    if is_transient_resource_failure "$rc" "$output_file" && [[ "$attempt" -lt "$attempts" ]]; then
      echo "Transient local resource failure during $name (exit $rc); retrying in ${delay_seconds}s ($attempt/$attempts)..." >&2
      rm -f "$output_file"
      sleep "$delay_seconds"
      continue
    fi

    rm -f "$output_file"
    echo "Expected exit status 1, got $rc" >&2
    return 1
  done
}

run_local_completion_summary_gate() {
  local report_file
  report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-completion-audit.json.XXXXXX")"
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
  evidence_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence.json.XXXXXX")"
  init_report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence-init.json.XXXXXX")"
  audit_report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence-audit.json.XXXXXX")"
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

run_production_evidence_explain_gate() {
  local explain_report_file
  explain_report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-evidence-explain.json.XXXXXX")"
  (
    cd backend
    uv run python scripts/ai_trading_v1_completion_audit.py --explain-production-evidence > "$explain_report_file"
  )
  cat "$explain_report_file"
  python3 - "$explain_report_file" <<'PY'
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

items = report.get("items") or []
items_by_id = {item.get("id"): item for item in items if isinstance(item, dict)}
order_backend_item = items_by_id.get("real_order_backend_handoff") or {}
schema = report.get("schema") or {}
production_evidence = report.get("production_evidence") or {}
checks = {
    "mode": report.get("mode") == "production_evidence_explain",
    "local_v1_accepted": report.get("local_v1_accepted") is True,
    "ready_for_live_orders_false": report.get("ready_for_live_orders") is False,
    "production_evidence_ready_false": production_evidence.get("ready") is False,
    "production_evidence_not_provided": production_evidence.get("provided") is False,
    "item_ids_exact": set(items_by_id) == expected_item_ids,
    "required_item_fields_present": "status=accepted" in (schema.get("required_item_fields") or []),
    "safe_ref_schemes_present": set(schema.get("safe_artifact_ref_schemes") or []) == {"https", "lark", "notion", "ops"},
    "real_order_backend_item_blocked": "external_evidence_item_not_provided" in (order_backend_item.get("blockers") or []),
    "forbidden_values_present": "API keys" in (order_backend_item.get("forbidden_values") or []),
    "operator_guidance_present": bool(order_backend_item.get("operator_guidance")),
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "production_evidence_explain_gate": "accepted" if not failed else "failed",
    "checked": checks,
    "ready_for_live_orders": report.get("ready_for_live_orders"),
    "real_order_backend_blockers": order_backend_item.get("blockers"),
}, ensure_ascii=False, indent=2, sort_keys=True))
if failed:
    raise SystemExit("Production evidence explain gate failed: " + ", ".join(failed))
PY
  rm -f "$explain_report_file"
}

run_production_operator_preflight_gate() {
  local preflight_report_file
  preflight_report_file="$(mktemp "${TMPDIR:-/tmp}/ai-trading-production-operator-preflight.json.XXXXXX")"
  set +e
  (
    cd backend
    env \
      -u AUTH_REQUIRE_VERIFIED_BEARER \
      -u AUTH_JWKS_URL \
      -u AUTH_JWT_ISSUER \
      -u AUTH_JWT_AUDIENCE \
      -u AUTH_JWT_ALGORITHMS \
      -u AUTH_ADMIN_USERNAMES \
      -u AI_TRADING_SIGNAL_GATEWAY_ENABLED \
      -u AI_TRADING_SIGNAL_GATEWAY_URL \
      -u AI_TRADING_SIGNAL_GATEWAY_TOKEN \
      -u AI_TRADING_PRODUCTION_HANDOFF_APPROVED \
      -u AI_HARD_MAX_ORDER_NOTIONAL_USD \
      -u AI_HARD_REQUIRE_STOP_LOSS \
      -u AI_HARD_REQUIRE_TAKE_PROFIT \
      uv run python scripts/ai_trading_v1_production_operator_preflight.py --skip-local-runtime --strict \
        > "$preflight_report_file"
  )
  local rc=$?
  set -e
  cat "$preflight_report_file"
  if [[ "$rc" -ne 1 ]]; then
    echo "Expected production operator preflight to stay blocked with exit status 1, got $rc" >&2
    rm -f "$preflight_report_file"
    return 1
  fi
  # REDACTED_SENSITIVE_PREFLIGHT_VALUE is covered by the backend regression for secret-like evidence paths.
  python3 - "$preflight_report_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    report = json.load(handle)

components = report.get("components") or {}
local_runtime = components.get("local_runtime") or {}
summary = report.get("summary") or {}
blockers = report.get("blockers") or []
checks = {
    "mode": report.get("mode") == "ai_trading_production_operator_preflight",
    "preflight_ready_false": report.get("preflight_ready") is False,
    "live_orders_false": report.get("ready_for_live_orders") is False,
    "completion_blocker": "completion:live_orders_not_ready" in blockers,
    "production_readiness_blocker": "production_readiness:not_ready" in blockers,
    "github_upload_deferred": summary.get("github_upload") == "deferred_by_user_request",
    "local_runtime_skipped": local_runtime.get("skipped") is True,
}
failed = [name for name, ok in checks.items() if not ok]
print(json.dumps({
    "production_operator_preflight_gate": "blocked_as_expected" if not failed else "failed",
    "checked": checks,
}, ensure_ascii=False, indent=2, sort_keys=True))
if failed:
    raise SystemExit("Production operator preflight gate failed: " + ", ".join(failed))
PY
  rm -f "$preflight_report_file"
}

run_runtime_readiness_with_retry() {
  local attempts="${AI_TRADING_RUNTIME_READINESS_ATTEMPTS:-24}"
  local delay_seconds="${AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS:-5}"
  local attempt

  if [[ -z "$attempts" || "$attempts" =~ [^0-9] || "$attempts" -lt 1 ]]; then
    attempts=24
  fi
  if [[ -z "$delay_seconds" || "$delay_seconds" =~ [^0-9] || "$delay_seconds" -lt 1 ]]; then
    delay_seconds=5
  fi

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

  echo "Runtime readiness still blocked after $attempts attempts; runtime mirror freshness remained enforced." >&2
  return 1
}

cd "$REPO_ROOT"

run_step "Local dev shell syntax" \
  bash -lc "bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh scripts/local-dev/install_launch_agent.sh scripts/local-dev/ai_trading_local_supervisor.sh"

run_step "Backend compile check" \
  bash -lc "cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_production_handoff_service.py services/ai_trading_production_readiness_service.py database/migrations/add_ai_trading_agent_session_fields.py scripts/ai_trading_v1_live_stack_acceptance.py scripts/ai_trading_v1_acceptance_smoke.py scripts/ai_trading_model_adjust_live_acceptance.py scripts/ai_trading_v1_env_check.py scripts/ai_trading_production_handoff_check.py scripts/ai_trading_v1_production_readiness_check.py scripts/ai_trading_v1_production_operator_preflight.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py"

run_step "AI Trading backend regression" \
  bash -lc "cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q"

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

run_step "Production operator preflight remains blocked" \
  run_production_operator_preflight_gate

run_step "Local V1 completion boundary audit" \
  run_local_completion_summary_gate

run_expected_failure "Production completion boundary audit remains blocked" \
  bash -lc "cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-production"

run_step "Production evidence explain mode gate" \
  run_production_evidence_explain_gate

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
