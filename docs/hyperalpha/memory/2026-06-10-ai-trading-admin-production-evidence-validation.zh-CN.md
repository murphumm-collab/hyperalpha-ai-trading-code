# AI Trading Admin Production Evidence Validation 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- 后端新增 `/api/ai-trading/admin/production-evidence-validate`，仅 admin/operator 可访问。
- 该接口只接受请求体里的 evidence JSON object，不接受 production evidence 文件路径，不写 DB，不调用模型、交易所、GitHub 或订单后端。
- 校验逻辑复用 completion audit 的外部 evidence schema：7 个固定 item、timezone-aware timestamp、bounded text、safe artifact refs、未知字段/未知 item id/secret pattern fail closed。
- 即使 submitted evidence 完整 accepted，Admin validation API 也保持 `ready_for_live_orders=false`，只返回 `production_track=external_evidence_accepted_pending_explicit_confirmation`，不能作为实盘切换开关。
- Settings Admin AI Trading Production Evidence 区块新增 dry-run JSON validator，结果只通过 `extractAiTradingProductionEvidenceExplain` 安全投影显示 accepted/required、live-order blocked、evidence blockers、blocked item labels，不渲染 evidence 文件路径、env token/API key 名或 raw context summary。
- completion audit 的 `status_progress_marker` 现在要求状态文档包含 `AI Trading admin production evidence validation API` 和 `AI Trading admin production evidence validation UI` Done 标记。

## 已验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py api/ai_trading_routes.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py -q`：41 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：106 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：重试后通过；覆盖 106 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#80`、signal event `#78`、`agent_sessions.total=66`、`handoff_attempts.total=76`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 安全边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- Admin evidence validation 只是 dry-run 校验；真实 live ready 仍必须走 repo-external/private ops evidence、strict production audit、显式 live cutover 确认。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
