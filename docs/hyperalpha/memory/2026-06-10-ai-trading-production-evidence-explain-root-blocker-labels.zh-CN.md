# AI Trading Production Evidence Explain Root Blocker Labels 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Settings/Admin production evidence explain view 现在会在 root-level `productionEvidence.blockers` 非空时显示一个只读 Blockers 摘要。
- 该摘要复用 `formatAiTradingProductionEvidenceBlocker`，与 dry-run validation 的 root blocker 和 item blocker 标签保持一致，避免运营看到原始 `external_evidence_*` blocker id。
- Frontend source guard 新增 explain root blocker 渲染检查；completion audit 新增 `| AI Trading production evidence explain root blocker labels | Done |` gate。

## 验证结果

- Py compile：`cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py` 通过。
- Focused：`cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q` 返回 75 passed。
- Aggregate：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 160 passed、14 个既有 UTC deprecation warnings。
- Build：`cd frontend && npm run build` 通过，只有既有 browser-baseline/Browserslist/chunk-size warnings。
- Playwright smoke：`/app/ai-trading` 渲染 AI Trading runtime cards，显示 `Sessions 97`、`Specs 112`、`Signals 110`、`Attempts 108`；`/#settings` 跳过本地 onboarding 后渲染 Settings shell。未输入 API key；console 只有既有静态资源 404 和 `ContactDialog` ref warning。
- 本地验收：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 通过，继续覆盖 default production readiness DB-audit blocker；最新 mock handoff 证据为 spec `#112`、signal event `#110`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=97`、`handoff_attempts.total=108`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- 本轮只增强 admin explain view 的 root blocker 可读性，不改变 `ready_for_live_orders=false` 的默认生产边界。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
