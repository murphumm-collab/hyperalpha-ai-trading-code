# AI Trading Production Evidence Blocker Labels 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Settings/Admin 的 AI Trading Production Evidence explain 与 dry-run validation 视图现在使用 `formatAiTradingProductionEvidenceBlocker` 显示可读 blocker 标签，而不是把 `external_evidence_*` 内部标识作为主要 UI 文案。
- 覆盖了 production evidence 的常见 blocker，包括 run id、cutover approval、cutover window、timestamp、secret scan、schema/text bounds、summary terms，以及最近新增的 `external_evidence_artifact_ref_reused_across_items` 和 `external_evidence_artifact_ref_duplicate_in_item`。
- Frontend source guard 新增检查，确保 explain item blockers、validation root blockers、validation item blockers 都走 production-evidence 专用 formatter；completion audit 新增 `| AI Trading production evidence blocker labels | Done |` gate。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：73 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：158 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`，`ready_for_live_orders=false`，`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 158 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#109`、signal event `#107`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=95`、`handoff_attempts.total=105`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- 本轮只是增强管理员 evidence blocker 可读性和回归护栏，不改变 `ready_for_live_orders=false` 的默认生产边界。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
