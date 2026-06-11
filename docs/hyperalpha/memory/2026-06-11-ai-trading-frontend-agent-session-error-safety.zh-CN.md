# AI Trading Frontend Agent-Session Error Safety 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- `frontend/app/lib/aiTradingReadiness.ts` 新增 `formatAiTradingAgentSessionApiError`，只把已知 agent-session detail/code 和 HTTP status 映射成短标签。
- `frontend/app/components/hyper-ai/HyperAiPage.tsx` 的 agent-session detail/load/compress/save/archive 失败路径改为使用安全 formatter，不再把 raw `data.detail` 或 thrown `err.message` 渲染到 UI。
- 敏感 `context_summary` 写入拒绝信息只显示为 `Context summary contains sensitive text`；helper 源码也避免出现裸 `context_summary` 字段，保留既有 counts-only/source-guard 约束。
- `backend/tests/test_ai_trading_frontend_readiness_source.py` 新增 source guard，证明 agent-session 错误路径使用 `formatAiTradingAgentSessionApiError(res.status, data.detail, fallback)` 和 network fallback，不使用 `throw new Error(data.detail...)` 或 `e instanceof Error ? e.message`。
- Completion audit 新增状态 gate：`| AI Trading frontend agent-session error safety | Done |`。

## 当前验证状态

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：98 条通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：186 条通过，保留 15 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，保留既有 Browserslist/baseline/dynamic-import/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`、latest memory pointer accepted、local blockers 为空。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 local dev shell syntax、backend compile、186 条 AI Trading regression、API smoke、默认生产 handoff/readiness/DB-audit blockers、completion boundary、production evidence gates、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。
- 本轮 runtime readiness 第 1 次等待 frontend/backend/mock gateway 冷启动，第 2 次等待 backend，第 3/24 次返回 `ready=true`，`runtime_gateway.mode=http`、`target_kind=local_mock`、`runtime_mirror.current=true`、`runtime_agent_context_budget.secret_policy=counts_only_no_summary_text`。
- 最新 live local mock handoff 证据：strategy spec `#129`、signal event `#127`、handoff attempt `#125`、gateway response `mock_accepted`、`agent_sessions.total=114`、`handoff_attempts.total=125`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮只收口 agent-session 前端错误显示，不改变后端拒绝逻辑、agent-session 多用户隔离、context summary 写入红线、model-adjust、signal handoff 或订单后端行为。
- default production readiness DB-audit blocker 仍保留在一键本地验收中；本地 V1 accepted 不等于 production live-order ready。
- GitHub 上传：按用户要求跳过；`codex/ai-agent-multitenant-foundation` 分支只做本地提交，不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
