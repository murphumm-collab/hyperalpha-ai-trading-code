# 2026-06-10 AI Trading Runtime Handoff Attempt Observability Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading runtime status 现在包含 current-user handoff attempt 可观测性汇总。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- Backend runtime：
  - `/api/ai-trading/runtime` 新增 `handoff_attempts`。
  - 字段包括 `total`、`by_result`、`gateway_ready`、`gateway_not_ready`、`latest`。
  - `latest` 只包含 `id`、`signal_event_id`、`strategy_spec_id`、`symbol`、`action`、`result`、`gateway_ready`、`created_at`。
  - Runtime attempt 汇总按 current-user 过滤；Bob runtime 看不到 Alice attempts。
  - Runtime 不返回 gateway URL、gateway token、authorization header、API key 或 response body。

- Frontend：
  - `AiTradingRuntimeStatus` 新增 `handoff_attempts` 类型。
  - Hyper AI AI Trading runtime summary 从 5 列扩展到 6 列，新增 `Attempts`。
  - Attempts 卡显示总数、submitted 数和 `by_result` 分布。

- 文档：
  - Status doc 当前状态标记为 Runtime Handoff Attempt Observability。
  - V1 checklist 更新最新一键验收证据和 runtime attempt coverage。

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py api/ai_trading_routes.py tests/test_ai_trading_routes.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：35 passed
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：58 passed，3 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：passed，只有既有 browserslist/baseline/chunk-size warnings。
- `scripts/local-dev/install_launch_agent.sh`：passed。
- `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict`：`ready=true`，runtime 暴露 `handoff_attempts.total=29`。
- In-app Browser：跳过本地 onboarding 后 `/app/ai-trading` 显示 `Attempts`、`29 / 29 submitted`、`submitted:29`；没有输入 API key，没有触发 handoff。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；最新 live mock handoff 证据为 spec `#34`、signal event `#32`、`agent_sessions.total=19`、`handoff_attempts.total=30`。

## 下一步注意

- 后续如果继续扩展 runtime，可考虑把 failed/blocked attempts 做成 admin readiness warning，但不要让普通 runtime 泄露 error body 或 gateway target。
- 真实生产验收仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen 用户 profile、真实登录态和生产 readiness。
