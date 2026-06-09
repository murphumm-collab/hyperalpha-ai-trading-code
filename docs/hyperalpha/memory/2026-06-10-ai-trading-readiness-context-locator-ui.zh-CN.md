# 2026-06-10 AI Trading Readiness Context Locator UI

## 压缩记忆

- 本地切片：Settings Admin 的 AI Trading Production Readiness 面板现在会在 `Agent Context` component card 内展示最新 context locator：
  - `latest_over_budget`
  - `latest_redacted_context`
  - `latest_sensitive_context`
- UI 只显示 `id`、`agent_session_id`、`status`、`context_summary_chars`，不显示 `context_summary` 原文，避免把策略上下文、API key、token 或用户 secret 暴露到前端。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 admin 登录态 visual acceptance 仍未完成；本地 auth disabled 时 Admin readiness 控件隐藏是预期状态。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `frontend/app/components/settings/SettingsPage.tsx`
  - 新增 `AiTradingAgentContextLocatorView` 类型。
  - 新增 `getAgentContextLocators`，从 readiness `checks` 中安全解析 locator。
  - `Agent Context` readiness card 会显示 latest over-budget/redacted/sensitive locator 的 id/session/status/chars。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 `AI Trading production readiness agent context locator UI` Done 标记。
  - 记录前端 build 和本地 Settings shell 烟测。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 Settings Admin readiness 面板验收描述。

## 已验证

- `cd frontend && npm run build`：passed；剩余为既有 browser-baseline/Browserslist/chunk-size warning。
- In-app Browser 打开 `http://127.0.0.1:5174/#settings`，跳过本地 onboarding 后 Settings shell 正常渲染，无 visible error。
- 本地 auth disabled 下 Admin readiness controls 隐藏仍是预期；真实 admin 登录态 visual acceptance 仍是外部验收项。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、77 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- 最新一键验收 live mock handoff 证据：strategy spec `#58`、signal event `#56`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=43`、`handoff_attempts.total=54`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 本切片不改变交易 API、模型调用、handoff 或订单执行。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
