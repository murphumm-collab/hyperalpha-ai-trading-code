# AI Trading Runtime Readiness Retry Grace 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- 一键本地验收 runner 的 LaunchAgent runtime readiness 检查从固定 12 次等待改为默认 24 次、每次 5 秒，并支持 `AI_TRADING_RUNTIME_READINESS_ATTEMPTS` / `AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS` 环境变量覆盖。
- retry grace 不放松安全边界：每次 readiness 仍运行 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`， stale runtime mirror 仍会被阻断。
- 失败提示改为 `Runtime readiness still blocked ... runtime mirror freshness remained enforced.`，明确慢启动可以重试，但 runtime mirror freshness gate 没有被弱化。
- Completion audit 新增 runner/status gate：如果后续有人删掉可配置等待窗口、freshness-enforced 失败提示或 `| AI Trading runtime readiness retry grace | Done |` 标记，本地完成审计会失败。

## 当前验证状态

- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh scripts/local-dev/install_launch_agent.sh scripts/local-dev/ai_trading_local_supervisor.sh`：通过。
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：78 条通过，包含 runtime readiness retry grace 缺失时的负向完成审计。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：175 条通过，保留 15 条既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker、175 条 AI Trading regression、frontend build、runtime mirror 同步、`--require-runtime-mirror-current` 冷启动重试和 live local mock handoff；runtime readiness 第 1-2 次为正常冷启动等待且 `runtime_mirror.current=true`，第 3/24 次返回 `ready=true`。
- 最新 live local mock handoff 证据：strategy spec `#124`、signal event `#122`、handoff attempt `#120`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=110`、`handoff_attempts.total=120`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮只提升本地 LaunchAgent cold-start acceptance 稳定性，不触发真实模型调用、真实订单后端 handoff、真实交易所执行或 production evidence 持久化。
- default production readiness DB-audit blocker 仍保留在一键本地验收中；本地 V1 accepted 不等于 production live-order ready。
- GitHub 上传：按用户要求跳过；`codex/ai-agent-multitenant-foundation` 分支只做本地提交，不 push、不 merge。
- 继续开发/验收入口仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
