# AI Trading Model Setup Shortcut 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Hyper AI AI Trading Model runtime 卡片现在有 icon-only setup 按钮。
- 该按钮打开现有 `LLMConfigModal`，复用原有 `/api/hyper-ai/profile/llm` 保存/测试流程，不新增交易页专用模型配置接口。
- source guard 证明 setup shortcut 只调用 `setShowConfigModal(true)`，不在 AI Trading runtime card/action UI 里渲染 `llm_api_key`、`llm_base_url`、`api_key`、`base_url`。
- completion audit 新增 fail-closed marker：缺少 `| AI Trading model setup shortcut | Done |` 时本地 V1 不能被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：47 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：128 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 128 条 AI Trading 回归、frontend build、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#92`、signal event `#90`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=78`、`handoff_attempts.total=88`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- Playwright smoke：打开 `http://127.0.0.1:5174/app/ai-trading`，跳过本地 onboarding 且未输入 API key；AI Trading runtime cards 正常渲染，`data-testid="ai-trading-model-config-button"` 点击后打开现有 `Hyper AI 配置` LLM config modal。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
