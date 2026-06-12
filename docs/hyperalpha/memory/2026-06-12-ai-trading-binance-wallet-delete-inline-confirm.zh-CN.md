# AI Trading Binance Wallet Delete Inline Confirm Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- Binance Futures API wallet deletion 改为页面内确认：
  - `BinanceWalletSection.tsx` 新增 per-environment inline checkbox：`binance-wallet-delete-confirm`。
  - delete handler 不再调用浏览器原生 `confirm` / `window.confirm`。
  - delete button 在 `!deleteWalletConfirmed[environment]` 时 disabled。
  - handler 会二次检查 `deleteWalletConfirmed[environment]`，未确认时阻断并显示安全错误。
  - account changes、钱包不存在、delete attempt 结束后都会清空确认状态，避免跨账号或失败后复用旧确认。
- 新增 frontend source guard：
  - 锁定 Binance wallet delete handler 内不出现 `confirm(` / `window.confirm`。
  - 锁定 handler 检查 `deleteWalletConfirmed[environment]` 并在 attempt 后清空。
  - 锁定 panel 存在 inline confirmation checkbox。
  - 锁定 delete button 在未确认时 disabled。
- 强化 completion audit/status gate：
  - 新增 `| AI Trading Binance wallet delete inline confirm | Done |` 作为本地 V1 完成度 marker。
  - 缺少该 marker 时 `ai_trading_v1_completion_audit.py --strict-local` 会 fail closed。
- GitHub 上传：按用户要求跳过；不 push、不 merge。

## 当前验收证据

- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "binance_wallet_delete or hyperliquid_wallet_delete"`：2 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "binance_wallet_delete or hyperliquid_wallet_delete or current_repo_completion_audit"`：3 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`。
- `cd frontend && npm run build`：通过，仅剩既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warnings。
- 聚合 AI Trading 回归：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 `249 passed, 15 warnings`。
- 完整一键本地 V1 验收：首次两次在本机 `fork: Resource temporarily unavailable` 处提前退出，未计为通过；随后 `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 完整通过。
- 一键验收覆盖：249 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、default production handoff/readiness blockers、default production readiness DB-audit blocker、production operator preflight、production evidence gates、frontend build、LaunchAgent runtime sync、runtime readiness with `--require-runtime-mirror-current`、live local mock handoff。
- Runtime readiness：attempts 1-2 等 backend 冷启动，attempt 3/60 返回 `ready=true`、`runtime_mirror.current=true`、gateway `target_kind=local_mock`。
- 最新 local/mock evidence：spec `#159`、signal event `#157`、handoff attempt `#155`、gateway response `mock_accepted`、`agent_sessions.total=145`、`handoff_attempts.total=155`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 当前仍只能把本地 V1 作为本地/模拟订单后端验收；生产实盘仍必须通过外部 production evidence 和明确 cutover approval。
- 本轮代码提交后必须重新运行 `scripts/local-dev/install_launch_agent.sh` 与 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`，确认 runtime mirror 指向提交后的源码状态。
