# AI Trading Gateway Mode Guard 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- AI Trading V1 明确只接受 HTTP JSON signal gateway：新增 `AI_TRADING_SIGNAL_GATEWAY_MODE=http` 配置说明，默认仍为 `http`。
- `backend/services/ai_trading_production_handoff_service.py` 的生产 handoff readiness 现在返回非敏感 `gateway_mode` / `supported_gateway_modes`，并在 mode 不是 `http` 时添加 `signal_gateway_mode_must_be_http_json` blocker。
- 聚合生产 readiness 会把该 blocker 暴露为 `signal_handoff:signal_gateway_mode_must_be_http_json`，不返回 gateway token 原文。
- `/api/ai-trading/runtime` 现在返回非敏感 gateway `mode`，runtime handoff preflight 在非 HTTP mode 下添加 `production_gateway_mode_must_be_http_json`，本地 mock gateway 也不能绕过该 mode guard。
- `scripts/ai_trading_v1_live_stack_acceptance.py` 在 draft/handoff 前要求 runtime gateway `mode=http`、`target_kind=local_mock`、无 runtime blockers。
- Hyper AI AI Trading Gateway card 显示 `Local mock / http` 或 `External backend / http` 等非敏感模式标签；frontend source guard 防止 Gateway UI 使用 URL/token。
- `docs/hyperalpha/implementation-handoff.md` 和 `docs/hyperalpha/ai-trading-signal-gateway-contract.md` 已收紧为当前事实：V1 Agent 直接 handoff 只支持 HTTP JSON；RabbitMQ 只能作为未来显式 adapter 或订单后端内部实现，不能被误认为当前已接入。
- completion audit 新增 fail-closed marker：缺少 `| AI Trading gateway mode guard | Done |` 时本地 V1 不能被接受。

## 验证结果

- `cd backend && uv run python -m py_compile services/ai_trading_production_handoff_service.py services/ai_trading_strategy_spec_service.py scripts/ai_trading_v1_live_stack_acceptance.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_routes.py::test_ai_trading_signal_handoff_blocks_unsupported_gateway_mode tests/test_ai_trading_frontend_readiness_source.py::test_ai_trading_gateway_mode_ui_uses_non_secret_runtime_projection tests/test_ai_trading_v1_completion_audit.py::test_completion_audit_blocks_local_acceptance_when_gateway_mode_guard_marker_is_missing -q`：20 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：135 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`，无 local blockers。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 135 条 AI Trading 回归、frontend build、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#94`、signal event `#92`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=80`、`handoff_attempts.total=90`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
