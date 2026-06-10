# AI Trading Frontend Session Context Prompt Sanitizer 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Hyper AI `Load context` 现在会先调用 `sanitizeAiTradingAgentSessionContextForPrompt(context)`，再把 agent-session context packet `JSON.stringify` 到聊天输入。
- sanitizer 会递归处理 session context：敏感 key（API key、secret、token、private key、password、authorization、bearer）返回 `***`；疑似敏感的 `context_summary` / `agent_context_summary` 文本返回 `[redacted_sensitive_context]`。
- 这是前端提示词防线；正常 UI 展示仍走后端已脱敏 response，不改变 DB 审计行、不改变 handoff、不调用模型、不下单。
- `tests/test_ai_trading_frontend_readiness_source.py` 新增 source guard，证明 `Load context` 使用 `promptContext`，并禁止回归到 `JSON.stringify(context, null, 2)`。
- completion audit 的 `status_progress_marker` 现在要求 `| AI Trading frontend session context prompt sanitizer | Done |`，缺少该标记时本地 V1 acceptance 会失败。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：37 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：117 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 117 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#84`、signal event `#82`、`agent_sessions.total=70`、`handoff_attempts.total=80`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
