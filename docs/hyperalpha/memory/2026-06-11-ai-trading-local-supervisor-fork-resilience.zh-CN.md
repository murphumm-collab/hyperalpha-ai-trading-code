# AI Trading Local Supervisor Fork Resilience 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- `scripts/local-dev/ai_trading_local_supervisor.sh` 从 `set -euo pipefail` 调整为 `set -uo pipefail`，避免本机进程资源紧张时单个 `fork`/命令失败直接结束整个 LaunchAgent supervisor 循环。
- supervisor 的 `log()` 不再走热路径 `tee`，改为 shell `printf` 写 stdout 和日志文件，减少每次日志额外 fork。
- `ensure_postgres()` 先检查 `5432` 是否已监听；Postgres 已运行时不再每 30 秒额外调用 Docker 探测，降低常驻进程压力。
- frontend、mock gateway、backend 的子进程启动增加 `cd ... || exit 1` 和 `Failed to spawn ...` 记录；spawn 失败不会结束 supervisor 主循环，下一轮会继续尝试恢复。
- 一键本地验收新增 `Local dev shell syntax` gate，默认跑 `bash -n` 检查本地 dev/LaunchAgent 三个 shell 脚本。
- `backend/tests/test_ai_trading_env_check.py` 新增 source guard，防止 supervisor 退回 `set -e`、热路径 `tee`、重复 Docker probe 或静默 spawn 失败。
- Completion audit 新增 `| AI Trading local supervisor fork-pressure resilience | Done |` 状态 gate，并要求一键 runner 保留 `Local dev shell syntax`。

## 当前验证状态

- `bash -n scripts/local-dev/ai_trading_local_supervisor.sh scripts/local-dev/run_ai_trading_v1_local_acceptance.sh scripts/local-dev/install_launch_agent.sh`：通过。
- `cd backend && uv run python -m py_compile tests/test_ai_trading_env_check.py tests/test_ai_trading_v1_completion_audit.py scripts/ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_v1_completion_audit.py -q`：90 条通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：180 条通过，保留 15 条既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 local dev shell syntax、default production readiness DB-audit blocker、180 条 AI Trading regression、frontend build、runtime mirror 同步、`--require-runtime-mirror-current` 冷启动重试和 live local mock handoff；runtime readiness 第 1-2 次为正常冷启动等待且 `runtime_mirror.current=true`，第 3/24 次返回 `ready=true`。
- 最新 live local mock handoff 证据：strategy spec `#126`、signal event `#124`、handoff attempt `#122`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=111`、`handoff_attempts.total=122`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮只提升本机 LaunchAgent supervisor 的抗资源压力与自恢复能力，不改变真实模型调用、真实订单后端 handoff、真实交易所执行或生产 evidence 边界。
- default production readiness DB-audit blocker 仍保留在一键本地验收中；本地 V1 accepted 不等于 production live-order ready。
- GitHub 上传：按用户要求跳过；`codex/ai-agent-multitenant-foundation` 分支只做本地提交，不 push、不 merge。
- 继续开发/验收入口仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
