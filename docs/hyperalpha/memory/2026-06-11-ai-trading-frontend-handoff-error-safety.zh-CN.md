# AI Trading Frontend Handoff Error Safety 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Hyper AI AI Trading 前端的 signal handoff、handoff-attempt inspect、signal reject 三条高风险失败路径不再渲染 raw API `detail`、caught `err.message` 或订单后端异常原文。
- `frontend/app/lib/aiTradingReadiness.ts` 新增 `formatAiTradingSignalActionApiError`，只展示白名单状态、白名单 blocker code、安全 HTTP status 或通用 fallback。
- formatter 允许展示的 signal/handoff blocker 包括 `production_handoff_approval_required`、`signal_event_stale_for_handoff`、`agent_session_archived`、gateway 配置 blocker、signal boundary blocker 和 `strategy_backtest_required_before_handoff` 等安全标签。
- `backend/tests/test_ai_trading_frontend_readiness_source.py` 新增 source guard，证明上述三条失败路径都使用安全 formatter，并禁止回退到 `data.detail`、`typeof detail === 'string'`、`throw new Error(...)` 或 `e instanceof Error ? e.message`。
- Completion audit 新增 `| AI Trading frontend handoff error safety | Done |` 状态 gate；如果后续缺失该标记，本地 V1 完成验收会 fail closed。

## 当前验证状态

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：91 条通过。
- `cd frontend && npm run build`：通过，仅保留既有 browser-baseline/Browserslist/dynamic-import/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：177 条通过，保留 15 条既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker、177 条 AI Trading regression、frontend build、runtime mirror 同步、`--require-runtime-mirror-current` 冷启动重试和 live local mock handoff；runtime readiness 第 1-3 次为正常冷启动等待且 `runtime_mirror.current=true`，第 4/24 次返回 `ready=true`。
- 最新 live local mock handoff 证据：strategy spec `#125`、signal event `#123`、handoff attempt `#121`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=111`、`handoff_attempts.total=121`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮只收紧前端错误展示边界，不改变策略生成、signal 资格判断、订单后端 handoff 协议或真实交易执行。
- default production readiness DB-audit blocker 仍保留在一键本地验收中；本地 V1 accepted 不等于 production live-order ready。
- GitHub 上传：按用户要求跳过；`codex/ai-agent-multitenant-foundation` 分支只做本地提交，不 push、不 merge。
- 继续开发/验收入口仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
