# 2026-06-10 AI Trading Runtime Agent Context Budget

## 压缩记忆

- 本地切片：把 current-user agent-session context budget 暴露到 `/api/ai-trading/runtime`，并在 Hyper AI AI Trading Sessions runtime 卡片显示。
- 目标是让 To C 多用户/多会话 AI Trading 在共享 DeepSeek/Qwen 模型前，能看到当前用户上下文预算健康，但不读取或展示任何 raw context summary。
- 后端 runtime 新增 counts-only `agent_sessions.context_budget`：total/active/archived、with/empty summary、max summary chars、near/over budget counts、redacted/sensitive-looking counts 和 `secret_policy=counts_only_no_summary_text`。
- 前端 Sessions runtime 卡片根据后端 budget 显示 `ctx max` / `ctx watch` / `ctx over`，只展示计数和 max chars，不展示 summary 原文。
- 本切片不改变交易 API、模型 provider、handoff enablement 或订单执行；外部订单后端仍 disabled-by-default。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `backend/services/ai_trading_strategy_spec_service.py`
  - 新增 `_summarize_agent_session_context_budget(db, user_id=...)`。
  - `get_ai_trading_runtime_status` 的 `agent_sessions` 现在包含 active total 和 counts-only `context_budget`。
  - 查询严格按 current `user_id` 过滤，不返回 `context_summary`、session locator、API key、token 或 raw secret。
- `backend/tests/test_ai_trading_routes.py`
  - 新增 `test_ai_trading_runtime_reports_current_user_agent_context_budget_without_summaries`。
  - 覆盖 active/archived、near/over budget、redacted/sensitive-looking summary、Bob 隔离和 summary/tail/API-key 不泄露。
- `frontend/app/components/hyper-ai/HyperAiPage.tsx`
  - 扩展 runtime type，读取 `agent_sessions.context_budget`。
  - Sessions runtime 卡片新增 context health label 和 warning/error tone。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新一键验收到 80 条回归、route regression 到 37 条。
  - 记录 latest live mock handoff evidence：strategy spec `#62`、signal event `#60`、handoff attempts `58`。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 runtime agent context budget Done 标记。
  - 记录 focused test、route suite、frontend build、aggregate regression、LaunchAgent resync/env check、Browser visual check 和 one-key local acceptance evidence。

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py::test_ai_trading_runtime_reports_current_user_agent_context_budget_without_summaries -q`：1 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：37 passed。
- `cd frontend && npm run build`：passed；剩余为既有 browser-baseline/Browserslist/chunk-size warning。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：80 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、80 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local/production completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- `scripts/local-dev/install_launch_agent.sh` 已同步 runtime mirror；随后 `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict` 返回 `ready=true`，running runtime 包含 `agent_sessions.context_budget.total=48`、`active=47`、`archived=1`、`with_context_summary=2`、`redacted_context_summary_count=1`、`near_budget_count=0`、`over_budget_count=0`。
- In-app Browser 打开 `http://127.0.0.1:5174/app/ai-trading`，跳过本地 onboarding，未输入 API key，未触发 handoff；页面无 visible error，Sessions card 显示 `47 active` 和 `ctx watch 1`，Recent agent sessions 显示 `ctx 0 / 2000`。
- 最新一键验收 live mock handoff 证据：strategy spec `#62`、signal event `#60`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=47`、`handoff_attempts.total=58`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- 真实模型调用仍需要用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需要真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
- 实际 macOS 整机重启恢复、真实 admin visual、真实生产登录态 session detail、真实 exchange execution 仍是外部验收项。
