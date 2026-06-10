# 2026-06-10 AI Trading Admin Production Evidence UI

## 本轮完成

- 在 `codex/ai-agent-multitenant-foundation` 分支继续本地开发，GitHub 上传：按用户要求跳过；本轮不 push、不 merge。
- Settings Admin AI Trading 新增 Production Evidence UI，读取 `GET /api/ai-trading/admin/production-evidence-explain`。
- 前端 helper `extractAiTradingProductionEvidenceExplain` 将后端 explain payload 转成安全 view model，只渲染 accepted/required、evidence provided、live-order blocked、item status/blockers、artifact-ref count、bounded operator guidance 和 next actions。
- Settings 页面刷新 Admin 数据时会并行拉取 production readiness 与 production evidence explain；刷新按钮 loading/disabled 已覆盖 evidence explain loading。
- completion audit 的 `status_progress_marker` 现在要求状态文档包含 `AI Trading admin production evidence UI` Done 标记；缺少该标记时 local V1 acceptance fail closed。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py -q`：28 passed。
- `cd frontend && npm run build`：通过，仅有既有 browser-baseline/Browserslist/chunk-size warning。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：100 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：`local_v1_accepted=true`、`ready_for_live_orders=false`、`local_blockers=[]`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；最新证据 spec `#79`、signal event `#77`、`agent_sessions.total=65`、`handoff_attempts.total=75`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- Playwright smoke 打开 `http://127.0.0.1:5174/#settings`，跳过本地 onboarding 且未输入 API key，Settings shell 正常渲染；本地未登录/auth-disabled 状态下 admin 区块隐藏仍是预期。

## 安全边界

- UI source guard 证明 Settings 只使用 `extractAiTradingProductionEvidenceExplain` 的安全投影，不渲染 `production_evidence_file`、订单网关 token env 名、DeepSeek/Qwen/DashScope API-key env 名或 raw `context_summary`。
- default production readiness DB-audit blocker 仍保留；真实上线前不能把本地 mock readiness 当作 production ready。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收。
- 真实 macOS 整机重启恢复、真实 admin 登录态可视化验收、真实 production agent-session detail 验收、真实交易所执行仍是外部/生产验收项。
- 任何真实实盘切换都必须使用 repo 外或私有 ops 位置的 sanitized production evidence，并显式通过 `--allow-live-ready-from-evidence`；代码仓库内 evidence 不能解锁 live orders。
