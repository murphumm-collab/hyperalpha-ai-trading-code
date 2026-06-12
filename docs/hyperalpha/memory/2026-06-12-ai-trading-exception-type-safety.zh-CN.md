# 2026-06-12 AI Trading Exception Type Safety Memory

## 本轮新增

- AI Trading model-adjust 和 signal gateway handoff 失败路径新增 exception type 安全标签。
- 如果底层异常 class name 含 `api_key` / `token` / `secret` / `private_key` / `password` / `authorization` / `bearer` 或 URL 形态，后端 API detail、signal event `error_message`、handoff attempt `eligibility.gateway_response.error_type` 都只返回 `Exception`。
- 普通非敏感 exception type 仍可保留用于排查，例如既有 gateway 失败测试中的 `FakeGatewayError`。
- 保持状态码等非敏感排查信息，例如 `Signal gateway handoff failed: Exception (status 503)`。
- Completion audit 新增 marker：
  - `| AI Trading model/gateway exception type safety | Done |`

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py api/ai_trading_routes.py tests/test_ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "sensitive_exception_type or failed_gateway_handoff_audit_is_non_secret or model_adjustment_sanitizes_model_output_public_fields"`
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "model_gateway_exception_type_safety or current_repo_completion_audit"`
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`
- `cd frontend && npm run build`
- `git diff --check`

## 边界

- Branch: `codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。
- Local acceptance command: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`
- default production readiness DB-audit blocker: 未提供真实生产 DB audit / 外部 evidence 前保持阻断。
- 该切片只处理异常类型标签，不改变 model-adjust、strategy parser、handoff eligibility、order backend payload 或实盘放行逻辑。
- `ready_for_live_orders=false` 仍正确；真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态视觉验收、生产 agent-session 视觉验收、macOS 整机重启和真实交易所执行仍是外部 pending。
