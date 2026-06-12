# AI Trading Local Acceptance Transient Retry Hardening Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- 强化 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 的本地资源压力重试：
  - `is_transient_resource_failure` 不再只接受 exit code 2/128；只要命令非 0 且输出包含 `Resource temporarily unavailable` / `Failed to spawn` / `fork failed`，就按本机瞬时资源压力处理。
  - `run_expected_failure` 现在先检查 transient resource output，再接受预期的 exit 1，避免把 shell/Python spawn 失败误判成 production gate 的安全阻断通过。
  - `sleep_before_retry` 包住 retry sleep；如果 `sleep` 自己也因 fork 压力失败，runner 记录提示并继续重试，不直接 128 退出。
- 强化 completion-audit 测试自身的本机资源压力韧性：
  - 新增 `_run_subprocess_with_transient_retry`，仅对 `BlockingIOError`/errno 35 或明确系统级资源压力输出做短重试。
  - 普通 CLI 合约失败、断言失败、非资源错误不会被吞掉。
- 本轮只改本地验收 runner 和测试 harness；没有改变 AI Trading 下单、模型调用、订单后端、交易所执行或 production readiness 的实盘边界。
- GitHub 上传仍按用户要求跳过；不 push、不 merge。

## 验收证据

- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh && cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "transient_resource or transient_retry or expected_failure_gate or retry_sleep or current_repo_completion_audit"`：6 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：107 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub upload deferred。
- 聚合 AI Trading 回归：第一次 direct aggregate 没能 spawn `pytest`，外层仅资源错误重试后同一命令通过，`232 passed, 15 warnings`。
- 完整一键本地 V1 验收：第一次暴露 `Production evidence template remains blocked` retry 前的 `sleep` fork failure；加入 `sleep_before_retry` 后，`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 完整通过。
- 一键验收覆盖：232 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、default production handoff/readiness/DB-audit 阻断、default production readiness DB-audit blocker、production operator preflight 阻断、production evidence explain/template/initializer gates、frontend build、LaunchAgent runtime sync、runtime readiness with `--require-runtime-mirror-current`、live local mock handoff。
- Runtime readiness：attempt 3 曾因 `BlockingIOError` 暂时无法计算 source digest；attempts 4-12 等 backend；attempt 13/24 返回 `ready=true`、`runtime_mirror.current=true`、runtime gateway `mode=http` / `target_kind=local_mock`、Docker `required_for_readiness=false`、counts-only agent context budget。
- 最新 local/mock evidence：spec `#150`、signal event `#148`、handoff attempt `#146`、gateway response `mock_accepted`、`agent_sessions.total=136`、`handoff_attempts.total=146`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 本轮代码尚未完成本地提交后的 LaunchAgent runtime mirror 复核；提交后必须重新运行 `scripts/local-dev/install_launch_agent.sh` 与 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`。
