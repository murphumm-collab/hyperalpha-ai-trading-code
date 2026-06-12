# AI Trading Program Backtest Run Inline Confirm Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- Hyper AI AI Trading Program Backtest 历史运行入口改为内联确认：
  - current strategy card 新增 `ai-trading-program-backtest-run-confirm` checkbox。
  - `handleRunStrategyProgramBacktest` 不再调用浏览器原生 `window.confirm`。
  - run handler 必须先读取 `strategyProgramBacktestRunConfirmed`，未确认时用安全前端错误提示阻断。
  - current strategy 和 recent spec 的 run button 在未勾选确认框时保持 disabled。
  - Program Backtest SSE 完成并自动绑定结果后会清空确认状态，避免下一次误触发。
- 保持 preflight 与 execution 分离：
  - `handleStrategyBacktestPreflight` 仍只生成历史回测请求草案，不要求运行确认。
  - preflight 不启动 backtest、不 handoff、不下单。
- 新增 frontend source guard：
  - 锁定 Program Backtest run handler 内不出现 `window.confirm`。
  - 锁定 run handler 读取 `strategyProgramBacktestRunConfirmed` 并在完成后 reset。
  - 锁定 preflight block 不依赖 run confirmation。
  - 锁定 current/recent run controls 在未确认时 disabled。
- 强化 completion audit/status gate：
  - 新增 `| AI Trading frontend program backtest run inline confirm | Done |` 作为本地 V1 完成度 marker。
  - 缺少该 marker 时 `ai_trading_v1_completion_audit.py --strict-local` 会 fail closed。
- GitHub 上传：按用户要求跳过；不 push、不 merge。

## 验收证据

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "program_backtest_run_uses_inline_confirmation or program_backtest_result_uses_inline_input"`：2 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "frontend_program_backtest_run_inline_confirm or frontend_program_backtest_inline_no_prompt"`：2 passed。
- `cd frontend && npm run build`：通过，仅剩既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub upload deferred。
- 聚合 AI Trading 回归：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 `240 passed, 15 warnings`。
- 完整一键本地 V1 验收：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 复跑完整通过；第一次运行在通过前半段后以 code 128 提前退出，未计入验收。
- 一键验收覆盖：240 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、default production handoff/readiness blockers、default production readiness DB-audit blocker、production operator preflight 默认阻断、dirty-tree blocker、output redaction marker、production URL host/port/parse-error safety、completion boundary audit、production evidence gates、frontend strategy-action error safety、frontend backtest summary inline no-prompt、frontend program backtest inline no-prompt、frontend program backtest run inline confirm、frontend build、LaunchAgent runtime sync、runtime readiness with `--require-runtime-mirror-current`、live local mock handoff。
- Runtime readiness：attempts 1-15 等 frontend/backend/mock gateway/backend 冷启动、短超时或一次 recoverable `Failed to spawn: python`，attempt 16/24 返回 `ready=true`、`runtime_mirror.current=true`、runtime gateway `mode=http` / `target_kind=local_mock`、Docker `required_for_readiness=false`、counts-only agent context budget。
- 最新 local/mock evidence：spec `#155`、signal event `#153`、handoff attempt `#151`、gateway response `mock_accepted`、`agent_sessions.total=141`、`handoff_attempts.total=151`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 当前仍只能把本地 V1 判定为 `local_v1_accepted=true`；生产实盘仍必须通过外部 production evidence 和明确 cutover approval。
- `HyperAiPage.tsx` 中 agent-session archive 与 signal handoff 仍保留用户动作确认，尚未纳入本轮 Program Backtest run inline confirm slice；后续如要继续去浏览器原生弹窗，应分开做并补独立 source guard/验收。
- 本轮代码提交后必须重新运行 `scripts/local-dev/install_launch_agent.sh` 与 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`，确认 runtime mirror 指向提交后的源码状态。
