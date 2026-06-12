# 2026-06-12 Frontend Onboarding Error Safety Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- GitHub 上传：按用户要求跳过
- 分支纪律：不 push、不 merge
- 本地 V1：继续保持 `local_v1_accepted=true`、`ready_for_live_orders=false`
- 实盘生产：仍由真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态和真实交易所执行外部验收阻断
- 生产 DB-audit / production operator preflight / completion audit 默认仍保留 default production readiness DB-audit blocker

## 本轮新增

- Hyper AI onboarding 保存/测试 DeepSeek/Qwen 模型配置失败时复用 `formatAiTradingModelConfigApiError`
- Onboarding 不再把 raw backend detail、provider response、token validation error、network exception text 或 API key 相关错误直接渲染给 To C 用户
- Onboarding chat stream `error` chunk 不再渲染 `chunk.data?.message`，统一抛固定 `Stream error` label，由 UI 显示通用失败提示
- Source guard 覆盖 `formatAiTradingModelConfigApiError(saveRes.status, data.detail, fallback)`、`formatAiTradingModelConfigApiError(0, null, fallback)`、`.json().catch(() => ({}))` 和 raw `errData.detail` / `e.message` / `chunk.data?.message` 回归路径
- `ai_trading_v1_completion_audit.py --strict-local` 新增 status marker gate：`| AI Trading frontend onboarding error safety | Done |`

## 已跑验证

- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "onboarding_uses_safe_model_and_stream_errors or model_config_modal_uses_safe_api_error_formatter"`：2 passed
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "frontend_onboarding_error_safety or frontend_model_config_error_safety or current_repo_completion_audit"`：3 passed
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：passed
- `cd frontend && npm run build`：passed with existing Browserslist/baseline/dynamic-import/chunk-size warnings
- `cd backend && uv run pytest tests/test_ai_stream_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：267 passed, 17 warnings
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed；`local_v1_accepted=true`、`ready_for_live_orders=false`
- `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；runtime readiness attempt 3/60 returned `ready=true`

## 验收边界

- 一键本地验收仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准
- 最新本地 mock handoff evidence：spec `#167`、signal event `#165`、handoff attempt `#163`、gateway response `mock_accepted`、`agent_sessions.total=153`、`handoff_attempts.total=163`
- 未完成的外部项不要标记为 Done：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态、真实交易所执行
