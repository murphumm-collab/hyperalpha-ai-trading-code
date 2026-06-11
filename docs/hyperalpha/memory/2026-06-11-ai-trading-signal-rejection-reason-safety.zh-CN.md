# AI Trading Signal Rejection Reason Safety Memory

Date: 2026-06-11
Branch: `codex/ai-agent-multitenant-foundation`

## Current

- 本轮继续在 `codex/ai-agent-multitenant-foundation` 本地分支开发；GitHub 上传：按用户要求跳过，不 push、不 merge。
- 本轮目标是补齐 AI Trading signal reject `reason` 安全边界：该字段来自用户/API 请求，会进入 signal event `error_message` 和 `signal.review.reason`，并可能被前端放入后续 review prompt，不能携带 API key、token、secret、private key、password、authorization 或真实订单后端 URL。
- 新增写入前拒绝：reject signal 时如果 `reason` 含 secret-like 文本或 URL，API 返回 400，不把 signal event 从 `review_candidate` 改成 rejected，不写入敏感 reason。
- 新增响应层防御：历史/脏 `signal.review.reason` 如果含 secret-like 文本或 URL，在 signal detail response 中返回 `[redacted_sensitive_rejection_reason]`，但不修改 DB 审计 row；历史/脏 `event.error_message` 继续返回 `[redacted_sensitive_error_message]`。
- 上一轮 handoff `confirmation_source` 安全边界继续保持：敏感 confirmation source 写入前拒绝；历史/脏 `user_confirmation.source` 在 handoff attempts 和 agent-session context packet 中脱敏。
- default production readiness DB-audit blocker 仍保留；真实上线仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。

## Verification Notes

- Focused checks 已通过：`py_compile` 覆盖 strategy service、completion audit、route tests、completion tests；focused pytest 3 条覆盖敏感 signal reject reason 写入前拒绝、legacy polluted `review.reason` 响应脱敏、completion audit marker fail-closed。
- 新增 completion audit status marker：`| AI Trading signal rejection reason safety | Done |`；缺少该 marker 时本地完成度审计会失败。
- 本地最终验收命令仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准；该命令需要在本切片文档、状态和 latest memory 中保留，避免 completion audit 把未记录的一键验收误判为已完成。
- Route/completion boundary regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py -q` 返回 141 passing tests。
- Strict-local completion audit 已通过：`cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` 返回 `local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`local_blockers=[]`。
- Aggregate regression 已通过：`cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` 返回 206 passing tests with 15 existing UTC warnings；首次启动聚合命令前曾遇到 macOS transient process pressure，等待后重跑通过。
- Frontend build 已通过：`cd frontend && npm run build` 成功，仅保留既有 baseline-browser-mapping / Browserslist / dynamic-import / chunk-size warnings。
- 最新一键本地 V1 验收通过：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 覆盖 206 条 AI Trading 回归、frontend build、LaunchAgent runtime mirror sync、strict runtime readiness 和 live local mock handoff；runtime readiness 第 10/24 次返回 `ready=true`、`runtime_mirror.current=true`、gateway `mode=http` / `target_kind=local_mock`，第 9/24 次出现一次可恢复的 macOS `Resource temporarily unavailable` transient。
- 最新 live mock handoff 证据：strategy spec `#140`、signal event `#138`、handoff attempt `#136`、gateway response `mock_accepted`、`agent_sessions.total=125`、`handoff_attempts.total=136`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- 后续代码变更后仍需重跑 aggregate regression、frontend build、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
