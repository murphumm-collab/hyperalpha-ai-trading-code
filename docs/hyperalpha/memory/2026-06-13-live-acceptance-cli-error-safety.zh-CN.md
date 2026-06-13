# Live Acceptance CLI Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 AI Trading 本地/真实验收 runner 的错误输出面。
- 防止 `ai_trading_v1_live_stack_acceptance.py` 和 `ai_trading_model_adjust_live_acceptance.py` 在 HTTPError、URLError 或外层异常时把 raw HTTP body、provider exception、secret-like URL、Bearer token、API key、private key 或其他敏感文本写入 stdout JSON。
- 保持 live-stack runner 只能本地 mock handoff，live model-adjust runner 仍必须显式 `--confirm-live-model-call`，不改变 `ready_for_live_orders=false`。

## 已完成

- `backend/scripts/ai_trading_v1_live_stack_acceptance.py`
  - HTTPError 不再把 response body 拼进 RuntimeError。
  - URLError 只返回安全 exception type label。
  - `main()` 失败时输出 `_safe_failure_payload(exc)`，包含固定安全 `error` 和 bounded `error_type`。

- `backend/scripts/ai_trading_model_adjust_live_acceptance.py`
  - HTTPError 不再把 response body 拼进 RuntimeError。
  - URLError 只返回安全 exception type label。
  - `main()` 失败时输出 `_safe_failure_payload(exc)`，避免把真实模型/API 配置错误原文写进验收报告。

- `backend/tests/test_ai_trading_live_stack_acceptance.py`
  - 覆盖 ApiClient HTTPError body 含 secret-like 文本时，异常文本只保留 `HTTP 503`，不回显 body。
  - 覆盖 main failure report 遇到 secret-like RuntimeError 时返回固定安全错误 JSON。

- `backend/tests/test_ai_trading_model_adjust_live_acceptance.py`
  - 覆盖 ApiClient HTTPError body 含 secret-like 文本时，异常文本只保留 `HTTP 503`，不回显 body。
  - 覆盖 main failure report 遇到 secret-like RuntimeError 时返回固定安全错误 JSON。

- 验收链条
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_ai_trading_live_stack_acceptance.py` 和 `tests/test_ai_trading_model_adjust_live_acceptance.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading live acceptance CLI error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增 current repo source guard，以及缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_live_stack_acceptance.py scripts/ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py -q`：11 passing tests。
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_live_stack_acceptance.py scripts/ai_trading_model_adjust_live_acceptance.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_v1_completion_audit.py -q -k "live_acceptance_cli_error_safety or live_stack_acceptance_api_client_http_error_is_sanitized or live_stack_acceptance_main_failure_report_is_sanitized or live_model_adjust_acceptance_api_client_http_error_is_sanitized or live_model_adjust_acceptance_main_failure_report_is_sanitized"`：7 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_market_universe_error_safety.py tests/test_auth_jwks_error_safety.py tests/test_hyperliquid_market_data_error_safety.py tests/test_hyperliquid_symbol_service_error_safety.py tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：311 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`，latest memory accepted，7 个外部验收项仍按设计 pending。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- live-stack acceptance 仍要求 `--confirm-local-mock-handoff` 且只接受 local mock gateway。
- live model-adjust acceptance 仍要求 `--confirm-live-model-call`，不会接受或打印 API key。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 继续检查其他 operator-facing scripts，尤其是 env/runtime check 的错误字段，避免 raw network/OS exceptions 带入验收报告。
- 真实生产验收仍必须另走 production evidence：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
