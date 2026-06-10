# 2026-06-10 AI Trading Admin Production Evidence Explain API

## 本轮完成

- 在 `codex/ai-agent-multitenant-foundation` 分支继续本地开发，GitHub 上传：按用户要求跳过；本轮不 push、不 merge。
- 新增 admin-only API：`GET /api/ai-trading/admin/production-evidence-explain`。
- 该 API 复用 completion audit 的 `production_evidence_explain` 清单，返回 7 个外部生产验收 item、required schema fields、safe artifact-ref schemes、forbidden values、operator guidance 和当前 blocker。
- API 不接受任意 `production_evidence_file` 路径，不读用户指定服务端文件，不调用模型、交易所、GitHub 或订单后端，不提交 handoff，不解锁 live orders。
- 返回仍保持 `local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`，并在无外部 evidence 时让 `real_order_backend_handoff` 显示 `external_evidence_item_not_provided`。
- completion audit 的 `status_progress_marker` 现在要求状态文档包含 `AI Trading admin production evidence explain API` Done 标记；缺少该标记时 local V1 acceptance fail closed。

## 验证结果

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py::test_admin_can_read_ai_trading_production_evidence_explain_without_secret_leakage tests/test_ai_trading_production_readiness_api.py::test_ai_trading_production_evidence_explain_api_requires_admin_session -q`：2 passed，覆盖 admin-only、匿名 401、普通用户 403、schema/blocker 检查和 env secret 不泄露。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：24 passed，覆盖 admin explain API status marker fail-closed。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py -q`：7 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：98 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：`local_v1_accepted=true`、`ready_for_live_orders=false`、`local_blockers=[]`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；最新证据 spec `#78`、signal event `#76`、`agent_sessions.total=64`、`handoff_attempts.total=74`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 仍未完成

- default production readiness DB-audit blocker 仍应保留在本地 V1 验收路径里；真实上线前不能把本地 mock readiness 当作 production ready。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收。
- 真实 macOS 整机重启恢复、真实 admin 登录态可视化验收、真实 production agent-session detail 验收、真实交易所执行仍是外部/生产验收项。
- 任何后续真实实盘切换都必须使用 repo 外或私有 ops 位置的 sanitized production evidence，并显式通过 `--allow-live-ready-from-evidence`；代码仓库内 evidence 不能解锁 live orders。
