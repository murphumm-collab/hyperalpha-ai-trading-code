# AI Trading Production Evidence Frontend Error Safety 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Settings/Admin Production Evidence 的 explain、validate、template 三个前端请求失败路径不再把 `data.detail` 或 `err.message` 原样渲染到页面。
- 新增 `formatAiTradingProductionEvidenceApiError`，只显示 HTTP status、白名单 API 错误码、已知 production evidence blocker 标签或固定 fallback；未知 detail、数组型 validation error、代理/网络异常都不会把原始响应体、Authorization header、Bearer token、API key、订单后端 URL 或用户粘贴的 evidence 文本带回 UI。
- Admin evidence source guard 覆盖 `fetchAiTradingEvidenceExplain`、`validateAiTradingEvidence` 和 `loadAiTradingEvidenceTemplate`，证明这些路径使用安全 formatter，且不再出现 `throw new Error(data.detail)`、`data.detail || ...` 或 `err instanceof Error ? err.message`。
- Completion audit 新增 `| AI Trading production evidence frontend error safety | Done |` gate，并把本地验收标题推进到 `Local V1 Evidence Frontend Error Safety Accepted / Remote Push Skipped`。

## 当前验证状态

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：88 条通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：174 条通过，保留 15 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，剩余为既有 browser-baseline/Browserslist/dynamic-import/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker、174 条 AI Trading regression、frontend build、runtime mirror 同步、`--require-runtime-mirror-current` 冷启动重试和 live local mock handoff；最新证据为 strategy spec `#123`、signal event `#121`、handoff attempt `#119`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=109`、`handoff_attempts.total=119`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮不改变生产实盘边界，不触发真实模型调用、真实订单后端 handoff、真实交易所执行、GitHub 上传或 production evidence 持久化。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
