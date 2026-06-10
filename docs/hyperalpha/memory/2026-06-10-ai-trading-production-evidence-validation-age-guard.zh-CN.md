# AI Trading Production Evidence Validation Age Guard 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence 新增 item validation age 防护：每个 item 的 `validated_at` 不能比 root `generated_at` 早超过 7 天。
- Completion audit 新增 `external_evidence_validated_at_too_old` item blocker；即使 root `generated_at`/`expires_at` 是新时间，也不能用旧验收材料重新包装来解锁 `ready_for_live_orders`。
- `--explain-production-evidence`、admin explain API、admin dry-run validation API 暴露安全 schema 字段 `max_item_validation_age_days=7`。
- Settings/Admin Production Evidence explain 与 dry-run validation UI 显示 `Validation age: 7d`，只使用安全投影 `maxItemValidationAgeDays`，不展示原始 evidence 文本、审批引用或 secret。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence validation age guard | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- Production evidence template note max length：264 chars，仍满足 note bounds gate。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：73 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：144 passed，14 个既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 144 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。runtime readiness attempt 1 是正常冷启动等待，attempt 2 `ready=true`、`runtime_mirror.current=true`、`runtime_gateway.mode=http`、`target_kind=local_mock`。最新 local/mock 证据为 spec `#101`、signal event `#99`、gateway response `mock_accepted`、`agent_sessions.total=86`、`handoff_attempts.total=97`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成、缺少审批引用、已过期、有效期超过 7 天、root/item 时间戳超过当前时间 300 秒以上、或 item `validated_at` 比 root `generated_at` 早超过 7 天时，`ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
