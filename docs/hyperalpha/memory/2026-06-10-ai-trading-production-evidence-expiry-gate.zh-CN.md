# AI Trading Production Evidence Expiry Gate 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence 根 schema 新增 `expires_at`，必须是带时区 ISO-8601 timestamp。
- Completion audit 现在拒绝缺失/无时区/已过期/不晚于 `generated_at` 的 `expires_at`，即使传入 `--allow-live-ready-from-evidence` 也不能解锁 `ready_for_live_orders`。
- `--explain-production-evidence` 和 admin dry-run validation 会返回安全的 `production_evidence.expires_at` 投影，前端只展示该时间，不展示原始 `evidence_summary` 或任何 secret。
- Production evidence 模板新增 `expires_at: null` 和短 note；模板仍必须保持 blocked，不能作为实盘证据。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence expiry gate | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：68 passed。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：139 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过；`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`，无 local blockers。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 139 条 AI Trading 回归、frontend build、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#96`、signal event `#94`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=82`、`handoff_attempts.total=92`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成或已过期时 `ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
