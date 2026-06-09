# 2026-06-10 AI Trading Readiness Locator Source Guard

## 压缩记忆

- 本地切片：Settings Admin readiness 的 Agent Context locator 解析逻辑已从页面组件抽出到 `frontend/app/lib/aiTradingReadiness.ts`。
- 新增 `backend/tests/test_ai_trading_frontend_readiness_source.py` 作为源码守卫，断言 Settings UI 只使用安全 projection，不渲染 raw `context_summary` 字段。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 已把该源码守卫纳入 backend compile 和 AI Trading regression 门。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 admin 登录态 visual acceptance 仍未完成；本地 auth disabled 时 Admin readiness 控件隐藏是预期状态。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `frontend/app/lib/aiTradingReadiness.ts`
  - 新增 `AiTradingProductionComponent`、`AiTradingProductionReadiness`、locator meta/view 类型。
  - 新增 `extractAiTradingAgentContextLocators`，只投影 `id`、`agent_session_id`、`status`、`context_summary_chars`。
- `frontend/app/components/settings/SettingsPage.tsx`
  - 删除内联 locator parser，改为调用 `extractAiTradingAgentContextLocators`。
- `backend/tests/test_ai_trading_frontend_readiness_source.py`
  - 检查 SettingsPage 不包含 raw `context_summary`，并确认 helper 只允许 locator 字段。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - compile/regression 步骤纳入 `test_ai_trading_frontend_readiness_source.py`。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 `AI Trading production readiness locator source guard` Done 标记。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 AI Trading 回归数量和最新一键验收编号。

## 已验证

- `cd backend && uv run python -m py_compile tests/test_ai_trading_frontend_readiness_source.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q`：1 passed。
- `cd frontend && npm run build`：passed；剩余为既有 browser-baseline/Browserslist/chunk-size warning。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：78 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、78 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- 最新一键验收 live mock handoff 证据：strategy spec `#59`、signal event `#57`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=44`、`handoff_attempts.total=55`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 本切片不改变交易 API、模型调用、handoff 或订单执行。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
