# AI Trading Strategy Text Source Safety Memory

Date: 2026-06-12
Branch: `codex/ai-agent-multitenant-foundation`

## Current

- 本轮继续在 `codex/ai-agent-multitenant-foundation` 本地分支开发；GitHub 上传：按用户要求跳过，不 push、不 merge。
- 本轮目标是补齐 AI Trading strategy text/source 安全边界：strategy draft / adjust / model-adjust instruction、stop-loss/take-profit rule、model source、record source、spec metadata source 都是用户/API 可控输入，不能携带 API key、token、secret、private key、password、authorization 或订单后端 URL，也不能进入 DeepSeek/Qwen prompt、signal、gateway payload。
- 新增写入前拒绝：strategy draft text、model source、record source、spec metadata source、adjustment instruction/source、model-adjust instruction/source 含 secret-like 文本或 URL 时返回 400，不保存 strategy spec、不改变已保存 record、不调用模型。
- 新增响应层防御：历史/脏 strategy spec 的自由文本和 `source` 字段如果含 secret-like 文本或 URL，在 strategy detail、signal preview、signal event 和 gateway payload 中返回 `[redacted_sensitive_strategy_text]` 或 `[redacted_sensitive_strategy_source]`；DB 审计 JSON 保持原文。
- 上一轮 market context、backtest evidence、signal reject `reason`、handoff `confirmation_source`、handoff `error_message`、strategy-spec name、agent-session name 等安全边界继续保持。
- default production readiness DB-audit blocker 仍保留；真实上线仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。

## Verification Notes

- 编译已通过：`cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`。
- Focused route safety 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "strategy_text_and_source or strategy_spec_responses_redact_legacy_sensitive_text"` 返回 2 passing tests。
- Route regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py -q` 返回 51 passing tests。
- Focused completion-audit marker regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "strategy_text_source_safety or market_context_safety or status_progress_marker"` 返回 2 passing tests。
- 新增 completion audit status marker：`| AI Trading strategy text source safety | Done |`；缺少该 marker 时本地完成度审计会失败。
- Strict-local completion audit 已通过：`cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` 返回 `local_v1_accepted=true`、`ready_for_live_orders=false`、latest memory pointer accepted。
- Route/completion boundary regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py -q` 返回 150 passing tests。
- Aggregate AI Trading regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 215 passing tests，只有既有 UTC deprecation warnings。
- Frontend production build 已通过：`cd frontend && npm run build`，只有既有 baseline-browser-mapping / Browserslist / dynamic-import / chunk-size warnings。
- 一键本地 V1 验收已通过：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 完成 215 回归、API smoke、production blocker gates、completion boundary gates、frontend build、LaunchAgent runtime sync、runtime readiness 和 live local mock handoff。
- 最新一键证据：runtime readiness 第 5/24 次 `ready=true`，`runtime_mirror.current=true`，`runtime_gateway.target_kind=local_mock`，`runtime_config_blockers=[]`；live local mock handoff 返回 spec `#144`、signal event `#142`、handoff attempt `#140`、gateway response `mock_accepted`；runtime-after `agent_sessions.total=129`、`handoff_attempts.total=140`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- 后续代码变更后仍需重跑 route/completion boundary regression、aggregate regression、frontend build、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
