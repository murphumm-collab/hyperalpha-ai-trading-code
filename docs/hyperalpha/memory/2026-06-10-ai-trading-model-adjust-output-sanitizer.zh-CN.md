# AI Trading Model-Adjust Output Sanitizer 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- DeepSeek/Qwen model-adjust 返回的 `instruction`、`rationale`、`risk_notes` 现在在应用、返回或持久化前统一清洗。
- secret-like 文本会替换为 `[redacted_sensitive_text]`，覆盖 Authorization/Bearer、API key、token、secret、private key、password、`sk-...` 等模式。
- 直接执行/下单措辞会替换为 `[direct_order_intent_ignored]`，覆盖 submit/place order、market/limit order、auto/direct execution、立即下单、直接下单、市价单、限价单等模式。
- 被清洗的模型输出仍进入同一个安全 parser，只允许安全策略字段调整；不会创建 signal event，不会 handoff，不会下单。
- `metadata.model_adjustment` 记录 `model_output_sensitive_text_redacted` 和 `model_output_direct_order_intent_ignored`，`validation.warnings` 同步加入对应 warning，方便前端/审计识别模型输出被约束过。
- completion audit 新增 fail-closed marker：缺少 `| AI Trading model-adjust output sanitizer | Done |` 时本地 V1 不能被接受。

## 验证结果

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py -q`：74 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：120 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 120 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#86`、signal event `#84`、`agent_sessions.total=72`、`handoff_attempts.total=82`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
