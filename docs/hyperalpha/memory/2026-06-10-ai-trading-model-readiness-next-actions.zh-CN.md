# AI Trading Model Readiness Next Actions 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- `/api/ai-trading/runtime` 的 `model_adjustment` 现在返回非敏感 `next_actions`。
- 已覆盖 missing profile、missing user API key、credential unreadable、unsupported provider、missing model、missing provider endpoint 等 blocker。
- Hyper AI AI Trading Model runtime 卡片和 model-adjust disabled tooltip 会优先展示后端给出的安全 next action。
- `next_actions` 只说明配置步骤，不返回用户 API key、endpoint 原文、profile 原文或模型上下文。
- completion audit 新增 fail-closed marker：缺少 `| AI Trading model readiness next actions | Done |` 时本地 V1 不能被接受。

## 验证结果

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py -q`：56 passed。
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：46 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：127 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 127 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#90`、signal event `#88`、`agent_sessions.total=76`、`handoff_attempts.total=86`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`，并返回安全 next action `Create a Hyper AI model profile with DeepSeek or Qwen before model-adjust.`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
