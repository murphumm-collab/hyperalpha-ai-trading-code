# AI Trading Production Preflight Dirty-Tree Blocker Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- 强化 `backend/scripts/ai_trading_v1_production_operator_preflight.py` 的 Git governance：
  - production operator preflight 现在把任何未提交 source 改动作为上线切换 blocker：`git:working_tree_has_uncommitted_changes`。
  - 报告只返回 `dirty_entry_count` 和安全 next action，要求先 commit 或丢弃本地改动。
  - 报告不返回 dirty 文件名、patch 内容、敏感路径、env secret、API key、token 或订单后端 URL。
- 强化 completion audit/status gate：
  - 新增 `| AI Trading production operator preflight dirty-tree blocker | Done |` 作为本地 V1 完成度 marker。
  - 缺少该 marker 时 `ai_trading_v1_completion_audit.py` 会 fail closed。
- 更新 V1 checklist/status/memory，记录最新本地验收证据和仍未完成的外部验收项。
- GitHub 上传：按用户要求跳过；不 push、不 merge。

## 验收证据

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_production_operator_preflight.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_operator_preflight.py -q`：4 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "production_preflight_dirty_tree or production_operator_preflight or current_repo_completion_audit"`：4 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_operator_preflight.py -q`：163 passed。
- 聚合 AI Trading 回归：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 `234 passed, 15 warnings`。
- 完整一键本地 V1 验收：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 完整通过。
- 一键验收覆盖：234 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、default production handoff/readiness 阻断、default production readiness DB-audit blocker、production operator preflight 默认阻断、production operator preflight dirty-tree blocker、production operator preflight output redaction marker、production evidence explain/template/initializer gates、frontend build、LaunchAgent runtime sync、runtime readiness with `--require-runtime-mirror-current`、live local mock handoff。
- Dirty-tree preflight evidence：开发中未提交 worktree 返回 `git:working_tree_has_uncommitted_changes`、`dirty_entry_count=5` 和安全 next action，未输出 dirty 文件名或 patch。
- Runtime readiness：attempts 1-4 等 frontend/backend/mock gateway/backend 冷启动，attempt 5 frontend/mock gateway 已 ready 但 backend 仍冷启动，attempt 6/24 返回 `ready=true`、`runtime_mirror.current=true`、runtime gateway `mode=http` / `target_kind=local_mock`、Docker `required_for_readiness=false`、counts-only agent context budget。
- 最新 local/mock evidence：spec `#152`、signal event `#150`、handoff attempt `#148`、gateway response `mock_accepted`、`agent_sessions.total=138`、`handoff_attempts.total=148`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 当前仍只能把本地 V1 判定为 `local_v1_accepted=true`；生产实盘仍必须通过外部 production evidence 和明确 cutover approval。
- 本轮代码提交后必须重新运行 `scripts/local-dev/install_launch_agent.sh` 与 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`，确认 runtime mirror 指向提交后的源码状态。
