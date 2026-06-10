# AI Trading Production Evidence Expiry Window 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence 的根级 `expires_at` 不仅必须未过期，还必须不超过 `generated_at` 后 7 天。
- Completion audit 新增 `external_evidence_expires_at_too_far` blocker；即使传入 `--allow-live-ready-from-evidence`，过长有效期也不能解锁 `ready_for_live_orders`。
- `--explain-production-evidence` schema 暴露安全字段 `max_evidence_validity_days=7`。
- Settings Admin Production Evidence explain / dry-run validation UI 显示 `Max validity: 7d`，只使用安全投影，不展示原始 `evidence_summary` 或任何 secret。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence expiry window | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：69 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：140 passed，14 个既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 140 条 AI Trading 回归、frontend build、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。首次完整 runner 在 API smoke 前遇到一次 macOS `fork: Resource temporarily unavailable`，重跑后完成；runtime readiness 在 attempt 11 返回 `ready=true`。最新 local/mock 证据为 spec `#97`、signal event `#95`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=83`、`handoff_attempts.total=93`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成、已过期或有效期超过 7 天时，`ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
