# AI Trading Production Evidence Summary Terms 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Completion audit 现在要求 accepted production evidence item 的 `evidence_summary` 必须包含该 item 对应的非敏感证明词，防止用泛泛 summary 绕过生产验收。
- `--explain-production-evidence` 会返回每个外部验收项的 `required_summary_terms` 和 `missing_summary_terms`，帮助运营按项补齐证据。
- Settings Admin Production Evidence dry-run UI 只展示 required/missing summary terms 的安全投影，不展示原始 `evidence_summary`。
- Production evidence 模板 note 已写明 accepted item 必须包含 required non-secret proof terms。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence summary terms | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py -q`：52 passed。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py::test_admin_can_validate_ai_trading_production_evidence_payload_without_live_unlock tests/test_ai_trading_production_readiness_api.py::test_admin_evidence_payload_validation_reports_secret_blocker_without_echoing_secret -q`：2 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：137 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`，无 local blockers。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 137 条 AI Trading 回归、frontend build、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#95`、signal event `#93`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=81`、`handoff_attempts.total=91`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
