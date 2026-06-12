# 2026-06-12 AI Stream Polling Error Redaction Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- GitHub 上传：按用户要求跳过
- 分支纪律：不 push、不 merge
- 本地 V1：继续保持 `local_v1_accepted=true`、`ready_for_live_orders=false`
- 实盘生产：仍由真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态和真实交易所执行外部验收阻断
- 生产 DB-audit / production operator preflight / completion audit 默认仍保留 default production readiness DB-audit blocker

## 本轮新增

- `/api/ai-stream/{task_id}` 和 `/api/ai-stream/{task_id}/status` 现在会把 failed task 的 `error` 字段投影为 stable public error code/message
- `error` / `interrupted` stream chunk payload 会被替换为 `ai_stream_task_failed` 安全 payload
- Raw provider output、Redis URL、Authorization header、task payload 或 credentials 不再通过 AI stream polling/status API 返回给 To C 前端
- DB task `error_message` 和后端日志仍保留原始失败信息用于内部审计/排查
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 已纳入 `tests/test_ai_stream_routes.py`
- `ai_trading_v1_completion_audit.py --strict-local` 新增 status marker gate：`| AI Trading AI stream polling error redaction | Done |`

## 已跑验证

- `cd backend && uv run pytest tests/test_ai_stream_routes.py -q`：2 passed
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "ai_stream_polling_error_redaction or ai_stream_routes_regression_gate or current_repo_completion_audit"`：3 passed
- `cd backend && uv run python -m py_compile api/ai_stream_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_stream_routes.py tests/test_ai_trading_v1_completion_audit.py`：passed
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：passed
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed，`local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub upload deferred、无 local blockers
- `cd backend && uv run pytest tests/test_ai_stream_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：260 passed, 17 warnings
- `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：completed
- 最新本地 mock handoff evidence：spec `#163`、signal event `#161`、handoff attempt `#159`、gateway response `mock_accepted`、`agent_sessions.total=149`、`handoff_attempts.total=159`
- Runtime readiness：attempts 1-6 等待 frontend/backend/mock gateway/backend 冷启动，attempt 7/60 返回 `ready=true`、`runtime_mirror.current=true`、`runtime_gateway.mode=http`、`target_kind=local_mock`

## 验收边界

- 一键本地验收仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准
- 生产 DB-audit / production operator preflight / completion audit 默认仍保留 default production readiness DB-audit blocker
- 未完成的外部项不要标记为 Done：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态、真实交易所执行
