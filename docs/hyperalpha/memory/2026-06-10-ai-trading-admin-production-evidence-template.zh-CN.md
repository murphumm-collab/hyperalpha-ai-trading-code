# AI Trading Admin Production Evidence Template 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- 后端新增 `/api/ai-trading/admin/production-evidence-template`，仅 admin/operator 可访问。
- 该接口复用 completion audit 的 `build_external_acceptance_evidence_template()`，返回 pending、无 secret 的 7 项外部验收 skeleton。
- Template API 不接受 evidence 文件路径，不返回 evidence 文件路径，不写 DB，不创建文件，不调用模型、交易所、GitHub 或订单后端，并始终返回 `ready_for_live_orders=false`。
- Settings Admin AI Trading Production Evidence 的 dry-run validator 增加 `Load template` 按钮，可把安全模板填入 evidence JSON textarea，再由 `/api/ai-trading/admin/production-evidence-validate` 做 dry-run 校验。
- completion audit 的 `status_progress_marker` 现在要求状态文档包含 `AI Trading admin production evidence template API` 和 `AI Trading admin production evidence template UI` Done 标记。

## 已知安全边界

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py -q`：45 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：110 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 110 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#81`、signal event `#79`、`agent_sessions.total=67`、`handoff_attempts.total=77`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- Template/validation/explain 都只是生产切换前的运维辅助，不会让 `ready_for_live_orders=true`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
