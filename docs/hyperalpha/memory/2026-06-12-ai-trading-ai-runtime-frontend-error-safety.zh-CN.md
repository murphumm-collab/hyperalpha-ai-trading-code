# 2026-06-12 AI Trading AI Runtime Frontend Error Safety Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- GitHub 上传：按用户要求跳过
- 分支纪律：不 push、不 merge
- 本地 V1：`local_v1_accepted=true`、`ready_for_live_orders=false`
- 实盘生产：仍由真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态和真实交易所执行外部验收阻断

## 本轮新增

- Settings Admin AI Runtime 加载失败路径改为使用 `formatAiTradingAiRuntimeApiError`
- `/api/ai-stream/admin/runtime` 的 401/403/404/429/500/503 等状态只映射为安全文案
- 已知 admin auth/role 错误只走白名单 label
- 不再把 raw `data.detail`、throw message、Redis URL、provider output、task payload 或 credentials 渲染到 Settings UI
- `tests/test_ai_trading_frontend_readiness_source.py` 新增 source guard，锁定 Settings loader 使用安全 formatter
- `ai_trading_v1_completion_audit.py --strict-local` 新增 status marker gate：`| AI Trading frontend AI runtime error safety | Done |`

## 已跑验证

- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "admin_ai_runtime_ui_uses_safe_api_error_formatter or admin_production_readiness_ui_uses_safe_api_error_formatter"`：2 passed
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "frontend_ai_runtime_error_safety or frontend_production_readiness_error_safety or current_repo_completion_audit"`：3 passed
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：passed
- `cd frontend && npm run build`：passed with existing Browserslist/baseline/dynamic-import/chunk-size warnings
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：253 passed, 15 warnings
- `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：completed
- 最新本地 mock handoff evidence：spec `#161`、signal event `#159`、handoff attempt `#157`、gateway response `mock_accepted`、`agent_sessions.total=147`、`handoff_attempts.total=157`
- Runtime readiness：attempts 1-12 等待 frontend/backend/mock gateway/backend 冷启动或一次 source-digest `Resource temporarily unavailable`，attempt 13/60 返回 `ready=true`、`runtime_mirror.current=true`、`runtime_gateway.mode=http`、`target_kind=local_mock`

## 验收边界

- 一键本地验收仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准
- 生产 DB-audit / production operator preflight / completion audit 默认仍保留 default production readiness DB-audit blocker
- 未完成的外部项不要标记为 Done：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态、真实交易所执行
