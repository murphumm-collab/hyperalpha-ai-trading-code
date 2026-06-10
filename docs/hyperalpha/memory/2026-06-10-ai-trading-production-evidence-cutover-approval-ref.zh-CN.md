# AI Trading Production Evidence Cutover Approval Ref 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence 新增根级 `cutover_approval_ref`，必须指向本次 live-order cutover window 的脱敏审批记录。
- 安全引用只允许 `ops://`、`lark://`、`notion://`、`https://`，并复用 artifact ref 的 localhost/private-network、credential、secret-pattern 检查。
- Completion audit 新增 `external_evidence_cutover_approval_ref_missing` 和对应 unsafe-ref blockers；即使传入 `--allow-live-ready-from-evidence`，缺少审批引用也不能解锁 `ready_for_live_orders`。
- `--explain-production-evidence`、admin explain API、admin dry-run validation API 只暴露 `cutover_approval_ref_present` 布尔值；前端 Settings/Admin 只显示 Cutover approval Provided/Not provided，不返回或渲染原始审批引用。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence cutover approval ref | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：71 passed，覆盖 missing/unsafe/localhost/secret-looking `cutover_approval_ref` 拒绝，以及 Settings/Admin 只读取安全布尔投影。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：142 passed，14 个既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 142 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。runtime readiness attempts 1-2 是正常冷启动等待，attempt 3 `ready=true`、`runtime_mirror.current=true`、`runtime_gateway.mode=http`、`target_kind=local_mock`。最新 local/mock 证据为 spec `#99`、signal event `#97`、gateway response `mock_accepted`、`agent_sessions.total=84`、`handoff_attempts.total=95`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成、缺少审批引用、已过期或有效期超过 7 天时，`ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
