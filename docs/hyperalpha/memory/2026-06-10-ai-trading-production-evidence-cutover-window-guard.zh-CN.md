# AI Trading Production Evidence Cutover Window Guard 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence 新增 root `cutover_window.start_at/end_at` 防护：两个字段必须是带时区 ISO-8601 时间戳，必须包含当前生产审计时间，且窗口最长 8 小时。
- Completion audit 新增 cutover window blockers：缺少 window、未知字段、未开始、已结束、窗口超过 8 小时、`generated_at` 早于/晚于窗口都会阻断 accepted production evidence。
- Production evidence template、`--explain-production-evidence`、admin explain API、admin dry-run validation API 暴露安全字段：`cutover_window_present`、`cutover_window_start_at`、`cutover_window_end_at`、`max_cutover_window_hours=8`。
- Settings/Admin Production Evidence explain 与 dry-run validation UI 展示 `Cutover window max: 8h` 和脱敏后的 start/end，只读取安全投影，不展示 raw evidence、审批原文或 secret。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence cutover window guard | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- Production evidence template note max length：264 chars，仍满足 note bounds gate。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：75 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：146 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 146 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。runtime readiness attempts 1-2 是正常冷启动等待，attempt 3 `ready=true`、`runtime_mirror.current=true`、`runtime_gateway.mode=http`、`target_kind=local_mock`。最新 local/mock 证据为 spec `#103`、signal event `#101`、gateway response `mock_accepted`、`agent_sessions.total=89`、`handoff_attempts.total=99`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成、缺少审批引用、没有 `cutover_window.start_at/end_at`、切换窗口不包含生产审计时间、切换窗口超过 8 小时、evidence 过期、有效期超过 7 天、root/item 时间戳超过当前时间 300 秒以上、或 item `validated_at` 比 root `generated_at` 早超过 7 天时，`ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
