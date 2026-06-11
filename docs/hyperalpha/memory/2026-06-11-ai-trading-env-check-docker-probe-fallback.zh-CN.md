# AI Trading Env-Check Docker Probe Fallback 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- `backend/scripts/ai_trading_v1_env_check.py` 增加 Docker probe fallback：当 Postgres `5432` 已监听时，Docker 只作为启动辅助依赖，不再因为一次 `docker version`/fork 失败阻断本地 V1 readiness。
- Docker probe 失败但 Postgres 已监听时，报告会保留非敏感诊断并增加 `docker.required_for_readiness=false`；如果 Docker 失败，额外标记 `readiness_blocker_suppressed=postgres_5432_already_listening`。
- Postgres 未监听时仍 fail closed：`postgres_5432_not_listening` 和 `docker_daemon_not_ready` 会继续给出启动 Docker/Postgres 的 next action。
- `backend/tests/test_ai_trading_env_check.py` 新增覆盖：Postgres/前端/后端/mock/runtime mirror 都 ready 时，Docker `BlockingIOError` 不阻断本地 V1；缺 Postgres 的既有 blocker 行为保持不变。
- Completion audit 新增 `| AI Trading env-check Docker probe fallback | Done |` 状态 gate；如果缺该标记，本地 V1 完成审计会 fail closed。

## 当前验证状态

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_env_check.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_v1_completion_audit.py -q`：92 条通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：182 条通过，保留 15 条既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：最终通过。第一次 login-shell 启动遇到 `/etc/zprofile` / shell `fork: Resource temporarily unavailable`；同命令用非 login shell 重跑后完成 local dev shell syntax、default production readiness DB-audit blocker、182 条 AI Trading regression、frontend build、runtime mirror 同步、`--require-runtime-mirror-current` 冷启动重试和 live local mock handoff。
- 本轮 runtime readiness 第 1-10 次为正常冷启动/本机资源压力等待且 `runtime_mirror.current=true`；第 11/24 次返回 `ready=true`，并显示 Docker `required_for_readiness=false` 因 Postgres 已监听。
- 最新 live local mock handoff 证据：strategy spec `#127`、signal event `#125`、handoff attempt `#123`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=112`、`handoff_attempts.total=123`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮只降低本地 env-check 对辅助 Docker probe 的误报，不降低 Postgres、backend、frontend、mock gateway、runtime mirror freshness、gateway local_mock 或 agent-session context budget 的严格 gate。
- default production readiness DB-audit blocker 仍保留在一键本地验收中；本地 V1 accepted 不等于 production live-order ready。
- GitHub 上传：按用户要求跳过；`codex/ai-agent-multitenant-foundation` 分支只做本地提交，不 push、不 merge。
- 继续开发/验收入口仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
