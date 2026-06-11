# AI Trading Market Context Safety Memory

Date: 2026-06-11
Branch: `codex/ai-agent-multitenant-foundation`

## Current

- 本轮继续在 `codex/ai-agent-multitenant-foundation` 本地分支开发；GitHub 上传：按用户要求跳过，不 push、不 merge。
- 本轮目标是补齐 AI Trading signal `market_context` 安全边界：`source`、`regime` 和数值字段来自 signal preview / signal event 请求，会进入 signal JSON、signal detail response、review prompt 和 gateway handoff payload，不能携带 API key、token、secret、private key、password、authorization 或真实订单后端 URL。
- 新增写入前拒绝：signal preview / signal event 创建时，如果 `market_context.source`、`regime` 或数值字段包含 secret-like 文本或 URL，API 返回 400，不创建新的 signal event。
- 新增响应层防御：历史/脏 signal JSON 的 market context 如果含 secret-like 文本或 URL，在 signal detail response 和 gateway payload 中返回 `[redacted_sensitive_market_context_text]` 或空数值；敏感 key 继续返回 `***`，但不修改 DB 审计 JSON。
- 上一轮 backtest evidence、signal reject `reason`、handoff `confirmation_source`、handoff `error_message`、strategy-spec name、agent-session name 等安全边界继续保持。
- default production readiness DB-audit blocker 仍保留；真实上线仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。

## Verification Notes

- Focused checks 已通过：`cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`。
- Focused route regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "market_context_rejects_sensitive_values or market_context_responses_redact_legacy_sensitive_values or signal_detail_and_gateway_payload_redact_sensitive_fields"` 返回 3 passing tests。
- Focused completion-audit marker regression 已通过：`cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`；`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "market_context_safety or backtest_evidence_safety or status_progress_marker"` 返回 2 passing tests。
- 新增 completion audit status marker：`| AI Trading market context safety | Done |`；缺少该 marker 时本地完成度审计会失败。
- Route/completion boundary regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py -q` 返回 147 passing tests。
- Aggregate AI Trading regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 212 passing tests，只有既有 UTC deprecation warnings。
- Frontend production build 已通过：`cd frontend && npm run build`，只有既有 baseline-browser-mapping / Browserslist / dynamic-import / chunk-size warnings。
- 一键本地 V1 验收已通过：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 完成 212 回归、API smoke、production blocker gates、completion boundary gates、frontend build、LaunchAgent runtime sync、runtime readiness 和 live local mock handoff。
- 最新一键证据：runtime readiness 第 11/24 次 `ready=true`，`runtime_mirror.current=true`，`runtime_gateway.target_kind=local_mock`，`runtime_config_blockers=[]`；live local mock handoff 返回 spec `#143`、signal event `#141`、handoff attempt `#139`、gateway response `mock_accepted`；runtime-after `agent_sessions.total=128`、`handoff_attempts.total=139`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- 后续代码变更后仍需重跑 route/completion boundary regression、aggregate regression、frontend build、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
