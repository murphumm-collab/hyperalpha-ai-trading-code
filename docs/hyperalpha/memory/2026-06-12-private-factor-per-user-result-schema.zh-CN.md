# 2026-06-12 Private Factor Per-User Result Schema Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- GitHub 上传：按用户要求跳过
- 分支纪律：不 push、不 merge
- 本地 V1：继续保持 `local_v1_accepted=true`、`ready_for_live_orders=false`
- 实盘生产：仍由真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态和真实交易所执行外部验收阻断
- 生产 DB-audit / production operator preflight / completion audit 默认仍保留 default production readiness DB-audit blocker

## 本轮新增

- 新增 `UserFactorValue` / `UserFactorEffectiveness` SQLAlchemy models
- 新增 `create_user_factor_result_tables.py` idempotent migration，并加入 `migration_manager.MIGRATIONS`
- 新表使用 `user_id + custom_factor_id` 隔离私有自定义 factor 结果，避免未来私有 factor 预计算落入按 `factor_name` 全局共享的 `factor_values` / `factor_effectiveness`
- Source guard 覆盖模型、迁移、migration-manager entry、user/custom factor FK、per-user unique keys
- `ai_trading_v1_completion_audit.py --strict-local` 新增 status marker gate：`| AI Trading private factor per-user result schema | Done |`

## 已跑验证

- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "private_factor_per_user_result_schema or private_factor_result_schema or current_repo_completion_audit"`：3 passed
- `cd backend && uv run python -m py_compile database/models.py database/migration_manager.py database/migrations/create_user_factor_result_tables.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：passed
- `DATABASE_URL=postgresql://alpha_user:alpha_pass@127.0.0.1:5432/alpha_arena uv run python -c "from database.migrations.create_user_factor_result_tables import upgrade; upgrade()"`：passed；follow-up information_schema query returned `['user_factor_effectiveness', 'user_factor_values']`
- `cd backend && uv run pytest tests/test_ai_stream_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：269 passed, 17 warnings
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed；`local_v1_accepted=true`、`ready_for_live_orders=false`
- `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；runtime readiness attempt 3/60 returned `ready=true`

## 验收边界

- 一键本地验收仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准
- 最新本地 mock handoff evidence：spec `#169`、signal event `#167`、handoff attempt `#165`、gateway response `mock_accepted`、`agent_sessions.total=154`、`handoff_attempts.total=165`
- 私有 factor 结果 schema 已存在；私有 factor 预计算 writer/reader 仍未验收，不要把 private custom factor precompute 标记为完成
- 未完成的外部项不要标记为 Done：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实管理员登录态、真实交易所执行
