# AI Trading Backtest Evidence Safety Memory

Date: 2026-06-11
Branch: `codex/ai-agent-multitenant-foundation`

## Current

- 本轮继续在 `codex/ai-agent-multitenant-foundation` 本地分支开发；GitHub 上传：按用户要求跳过，不 push、不 merge。
- 本轮目标是补齐 AI Trading backtest evidence 安全边界：`backtest_id` / `run_id` / `source` / `notes` 可来自手工 summary 或 backtest-result 绑定，会进入 strategy spec、signal event、agent review prompt 和 handoff payload，不能携带 API key、token、secret、private key、password、authorization 或真实订单后端 URL。
- 新增写入前拒绝：manual backtest summary / Program BacktestResult attach / latest attach 的用户可控 evidence 文本如果含 secret-like 文本或 URL，API 返回 400，不把敏感 evidence 写入 strategy spec。
- 新增响应层防御：历史/脏 strategy spec 的 backtest evidence 如果含 secret-like 文本或 URL，在 strategy detail 和 signal event response 中返回 `[redacted_sensitive_backtest_id]` / `[redacted_sensitive_backtest_source]` / `[redacted_sensitive_backtest_note]`，但不修改 DB 审计 JSON。
- 上一轮 signal reject `reason`、handoff `confirmation_source`、handoff `error_message`、strategy-spec name、agent-session name 等安全边界继续保持。
- default production readiness DB-audit blocker 仍保留；真实上线仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。

## Verification Notes

- Focused checks 已通过：`cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`。
- Focused route regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "backtest_summary_rejects_sensitive_evidence_fields or legacy_sensitive_backtest_evidence or signal_preview_response_redacts_attached_backtest_sensitive_fields"` 返回 3 passing tests。
- Focused completion-audit marker regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "backtest_evidence_safety or signal_rejection_reason_safety or status_progress_marker"` 返回 2 passing tests。
- 新增 completion audit status marker：`| AI Trading backtest evidence safety | Done |`；缺少该 marker 时本地完成度审计会失败。
- Route/completion boundary regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py -q` 返回 144 passing tests。
- Aggregate regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 209 passing tests with 15 existing UTC warnings。
- Frontend build 已通过：`cd frontend && npm run build` 成功，仅保留既有 baseline-browser-mapping / Browserslist / dynamic-import / chunk-size warnings。
- 最新一键本地 V1 验收通过：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 覆盖 209 条 AI Trading 回归、frontend build、LaunchAgent runtime mirror sync、strict runtime readiness 和 live local mock handoff；LaunchAgent sync 第一次遇到可恢复的 macOS `Resource temporarily unavailable` transient 后重试成功，runtime readiness 第 9/24 次返回 `ready=true`。
- 最新 live mock handoff 证据：strategy spec `#141`、signal event `#139`、handoff attempt `#137`、gateway response `mock_accepted`、`agent_sessions.total=126`、`handoff_attempts.total=137`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- 本地最终验收命令仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准；后续代码变更后仍需重跑 route/completion boundary regression、aggregate regression、frontend build、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
