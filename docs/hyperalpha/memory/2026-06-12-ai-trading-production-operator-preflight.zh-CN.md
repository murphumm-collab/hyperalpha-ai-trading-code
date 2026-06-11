# AI Trading Production Operator Preflight Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- 新增 `backend/scripts/ai_trading_v1_production_operator_preflight.py`，聚合 Git governance、本地 runtime readiness、production readiness、completion/evidence boundary。
- 该 CLI 是只读预检：不调用模型、不调用交易所、不调用订单后端、不调用 GitHub，不返回 env secret 值。
- 默认无真实生产 env / 无外部 production evidence 时，`--strict` 必须 blocked，核心 blocker 包含 `completion:live_orders_not_ready` 和 `production_readiness:not_ready`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 已加入 production operator preflight gate；默认 blocked 是本地验收的一部分，避免把 local V1 误判成实盘可切换。
- `ai_trading_v1_completion_audit.py --strict-local` 现在要求 status 文档包含 `| AI Trading production operator preflight | Done |`，并要求一键本地验收 runner 保留 preflight gate 短语。

## 验收证据

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_production_operator_preflight.py tests/test_ai_trading_production_operator_preflight.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_operator_preflight.py -q`：2 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "production_operator_preflight or current_repo_completion_audit"`：2 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_operator_preflight.py -q`：153 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：218 passed，15 个既有 UTC deprecation warnings。
- 默认 production operator preflight：`--skip-local-runtime --strict` 在缺真实生产 env / 外部 evidence 时按预期 exit 1，且 `local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub 上传仍为 deferred。
- 完整一键本地 V1 验收：第一次命中瞬态 macOS `fork: Resource temporarily unavailable`；等待后重跑 `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 成功。覆盖 218 条聚合回归、production operator preflight 默认阻断、frontend build、LaunchAgent runtime sync、runtime mirror freshness、live local mock handoff。runtime readiness 第 6/24 次返回 `ready=true`，最新证据为 spec `#145`、signal event `#143`、handoff attempt `#141`、`agent_sessions.total=130`、`handoff_attempts.total=141`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- default production readiness DB-audit blocker 仍是本地 V1 的安全阻断之一；生产 evidence 必须放在仓库外或私有 ops 位置。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
