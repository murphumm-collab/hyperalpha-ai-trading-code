# AI Trading Local Acceptance Transient Retry 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 增加一键本地验收步骤级 transient retry。
- 普通 `run_step` 和 `run_expected_failure` 都会对本机瞬时 fork/spawn 失败做有限重试，默认 `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=3`、`AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=5`。
- 只把 exit `2` / `128` 且输出包含 `Resource temporarily unavailable`、`Failed to spawn` 或 `fork failed` 的情况视为 transient local resource failure。
- 预期阻断 gate 仍必须返回 exit `1` 才算通过；意外成功、持久 CLI 错误、生产 readiness/handoff contract 失败都不会被吞掉。
- Completion audit 现在要求 runner 保留 `run_command_with_transient_retry`、transient retry 环境变量和 status Done marker `| AI Trading local acceptance transient retry | Done |`。

## 当前验证状态

- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh scripts/local-dev/install_launch_agent.sh scripts/local-dev/ai_trading_local_supervisor.sh`：通过。
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py -q`：94 条通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：184 条通过，保留 15 条既有 UTC deprecation warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`、latest memory pointer accepted、local blockers 为空。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 local dev shell syntax、backend compile、184 条 AI Trading regression、API smoke、默认生产 handoff/readiness/DB-audit blockers、completion boundary、production evidence gates、frontend build、runtime mirror sync、runtime readiness 和 live local mock handoff。
- 本轮 runtime readiness 第 1 次等待 frontend/backend/mock gateway 冷启动，第 2 次等待 backend，第 3/24 次返回 `ready=true`，`runtime_gateway.mode=http`、`target_kind=local_mock`、`runtime_mirror.current=true`、`runtime_agent_context_budget.secret_policy=counts_only_no_summary_text`。
- 最新 live local mock handoff 证据：strategy spec `#128`、signal event `#126`、handoff attempt `#124`、gateway response `mock_accepted`、`agent_sessions.total=113`、`handoff_attempts.total=124`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮只提高本地一键验收对 macOS 资源压力的抗抖能力，不降低 default production readiness DB-audit blocker、runtime mirror freshness、local mock gateway、signal-only/no-order、回测证据、用户确认或订单后端 handoff 安全边界。
- default production readiness DB-audit blocker 仍保留在一键本地验收中；本地 V1 accepted 不等于 production live-order ready。
- GitHub 上传：按用户要求跳过；`codex/ai-agent-multitenant-foundation` 分支只做本地提交，不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
