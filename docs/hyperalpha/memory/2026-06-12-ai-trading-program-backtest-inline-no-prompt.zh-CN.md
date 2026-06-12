# AI Trading Program Backtest Inline No-Prompt Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- Hyper AI AI Trading Program BacktestResult 手工 ID 绑定入口改为内联控件：
  - current strategy card 新增 Program Backtest Result ID 输入框。
  - current strategy card 的 link action 读取该输入，不再调用浏览器原生 `window.prompt`。
  - recent spec row 的 link action 也读取同一个内联输入，并先把选中的 strategy spec 载入当前卡片上下文。
  - recent Program Backtests 列表仍使用已知 `record.id` 直接绑定，不需要用户重复输入 ID。
- 新增 frontend source guard：
  - 锁定 `handleAttachProgramBacktestResult` 代码块内不出现 `window.prompt`。
  - 锁定该 handler 读取 `strategyProgramBacktestResultId.trim()`。
  - 锁定 current strategy card 存在 `data-testid="ai-trading-program-backtest-result-id"` 和 numeric input mode。
  - 锁定 recent spec row 调用 `handleAttachProgramBacktestResult(record.id, undefined, record)`，防止后续回退成无上下文手工 prompt。
- 强化 completion audit/status gate：
  - 新增 `| AI Trading frontend program backtest inline no-prompt | Done |` 作为本地 V1 完成度 marker。
  - 缺少该 marker 时 `ai_trading_v1_completion_audit.py --strict-local` 会 fail closed。
- 更新 V1 checklist/status/memory，记录最新本地验收证据和仍未完成的外部验收项。
- GitHub 上传：按用户要求跳过；不 push、不 merge。

## 验收证据

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "program_backtest_result_uses_inline_input or backtest_summary_uses_inline_inputs"`：2 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "frontend_program_backtest_inline_no_prompt or frontend_backtest_summary_inline_no_prompt"`：2 passed。
- `cd frontend && npm run build`：通过，仅剩既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub upload deferred。
- 聚合 AI Trading 回归：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 `238 passed, 15 warnings`。
- 完整一键本地 V1 验收：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 完整通过。
- 一键验收覆盖：238 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、default production handoff/readiness 阻断、default production readiness DB-audit blocker、production operator preflight 默认阻断、production operator preflight dirty-tree blocker、production operator preflight output redaction marker、production URL host secret redaction、production URL port safety、production URL parse-error safety、completion boundary audit、production evidence gates、frontend strategy-action error safety、frontend backtest summary inline no-prompt、frontend program backtest inline no-prompt、frontend build、LaunchAgent runtime sync、runtime readiness with `--require-runtime-mirror-current`、live local mock handoff。
- Runtime readiness：attempts 1-7 等 frontend/backend/mock gateway/backend 冷启动或短超时，attempt 8/24 返回 `ready=true`、`runtime_mirror.current=true`、runtime gateway `mode=http` / `target_kind=local_mock`、Docker `required_for_readiness=false`、counts-only agent context budget。
- 最新 local/mock evidence：spec `#154`、signal event `#152`、handoff attempt `#150`、gateway response `mock_accepted`、`agent_sessions.total=139`、`handoff_attempts.total=150`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 当前仍只能把本地 V1 判定为 `local_v1_accepted=true`；生产实盘仍必须通过外部 production evidence 和明确 cutover approval。
- 本轮代码提交后必须重新运行 `scripts/local-dev/install_launch_agent.sh` 与 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`，确认 runtime mirror 指向提交后的源码状态。
