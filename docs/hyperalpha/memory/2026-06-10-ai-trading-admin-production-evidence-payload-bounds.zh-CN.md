# AI Trading Admin Production Evidence Payload Bounds 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- 后端 `/api/ai-trading/admin/production-evidence-validate` 在进入 completion audit schema validation 和 secret scan 前，先限制 evidence JSON 序列化体积，超过 40000 bytes 直接返回 413。
- 同一 dry-run validator 会限制 `items` 字典 key 数量，超过 14 个直接返回 413，避免管理员把未知验收项、原始日志或 dump 塞进生产 evidence 校验入口。
- 413 错误只返回固定错误码：`production_evidence_payload_too_large` 或 `production_evidence_items_too_many`，不回显请求中的 secret-like 文本。
- Settings Admin evidence dry-run textarea 增加同样的 40000 字符上限和本地错误提示，避免浏览器端提交超大 JSON。
- completion audit 的 `status_progress_marker` 现在要求状态文档包含 `AI Trading admin production evidence payload bounds` Done 标记。

## 已知安全边界

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py -q`：48 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：113 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 113 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#82`、signal event `#80`、`agent_sessions.total=68`、`handoff_attempts.total=78`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- 这只是 admin dry-run 输入防护，不会保存 evidence，不会调用模型、交易所、GitHub 或订单后端，不会让 `ready_for_live_orders=true`。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
