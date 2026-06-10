# AI Trading Model Setup Runtime Refresh 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- AI Trading Model runtime 卡片的 setup 按钮仍打开现有 `LLMConfigModal`。
- LLM Config modal 保存成功后现在调用 `handleLLMConfigSaved()`，同时刷新 Hyper AI profile 和 AI Trading runtime/records。
- 这样用户从交易页配置 DeepSeek/Qwen 后，Model readiness 卡片、model-adjust 按钮 gate、recent specs/signals runtime 统计不会停留在保存前的旧状态。
- source guard 证明 `handleLLMConfigSaved()` 同时调用 `fetchProfile()` 与 `refreshAiTradingState()`，且 `LLMConfigModal` 使用 `onSaved={handleLLMConfigSaved}`。
- completion audit 新增 fail-closed marker：缺少 `| AI Trading model setup runtime refresh | Done |` 时本地 V1 不能被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：48 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：129 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`，latest memory pointer accepted。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 129 条 AI Trading 回归、frontend build、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#93`、signal event `#91`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=79`、`handoff_attempts.total=89`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
