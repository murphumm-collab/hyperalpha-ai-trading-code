# 2026-06-10 AI Trading Runtime Budget UI Source Guard

## 压缩记忆

- 本地切片：给 Hyper AI AI Trading Sessions runtime context budget UI 增加 frontend source guard。
- 目标是防止后续前端改动把 `/api/ai-trading/runtime` 的 agent-session context budget UI 从 counts-only 字段退化成渲染 raw `context_summary`。
- 现有 Settings Admin Agent Context locator UI source guard 已覆盖 production readiness locator；本切片把同一类防回归覆盖扩展到 `/app/ai-trading` 主页面的 Sessions runtime 卡片。
- 新测试只检查源码投影，不改变产品行为、交易 API、模型 provider、handoff enablement 或订单执行；外部订单后端仍 disabled-by-default。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `backend/tests/test_ai_trading_frontend_readiness_source.py`
  - 新增 `HYPER_AI_PAGE` source target。
  - 新增 `test_ai_trading_runtime_context_budget_ui_uses_counts_only_projection`。
  - 测试限定 runtime budget label block，要求使用 `near_budget_count`、`redacted_context_summary_count`、`sensitive_context_summary_count`、`over_budget_count`、`max_context_summary_chars`、`context_summary_max_chars`、`aiTradingAgentContextBudgetLabel()` 和 `aiTradingAgentContextBudgetTone`。
  - 去掉允许的 count/char 字段名后，断言 runtime budget block 和 Sessions card block 不包含 raw `context_summary`。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新一键验收到 83 条回归。
  - 更新 latest live mock handoff evidence：strategy spec `#64`、signal event `#62`、handoff attempts `60`。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 `AI Trading runtime budget UI source guard` Done 标记。
  - 记录 focused source guard、aggregate regression 和 one-key local acceptance evidence。

## 已验证

- `cd backend && uv run python -m py_compile tests/test_ai_trading_frontend_readiness_source.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q`：2 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：83 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、83 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local/production completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- 最新一键验收 live mock handoff 证据：strategy spec `#64`、signal event `#62`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=49`、`handoff_attempts.total=60`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- 真实模型调用仍需要用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需要真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
- 实际 macOS 整机重启恢复、真实 admin visual、真实生产登录态 session detail、真实 exchange execution 仍是外部验收项。
