# AI Trading Frontend Model-Adjust Output Safety 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Hyper AI AI Trading 当前策略卡片现在会显示 `data-testid="ai-trading-model-output-safety-warning"` 安全提示。
- 当后端 `validation.warnings` 或 `metadata.model_adjustment` 表明模型输出曾被清洗时，前端显示 `Model output redacted` / `Direct order intent ignored`。
- DeepSeek/Qwen model-adjust 后生成的 review packet 现在包含非敏感 `model_output_safety`，包括 `sensitive_text_redacted`、`direct_order_intent_ignored`、`validation_warnings`。
- 前端 source guard 新增 `test_ai_trading_model_adjust_output_safety_is_visible_in_frontend`，防止后续删除 warning UI 或 review packet 安全字段。
- completion audit 新增 `| AI Trading frontend model-adjust output safety | Done |` fail-closed marker。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：41 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：122 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 122 条回归、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。最新证据 spec `#87`、signal event `#85`、`agent_sessions.total=73`、`handoff_attempts.total=83`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、macOS 整机重启、真实交易所执行仍是外部未验收项。
