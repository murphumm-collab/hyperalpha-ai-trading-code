# 2026-06-10 AI Trading Readiness Locator Next Actions

## 压缩记忆

- 本地切片：production readiness 的 agent-session context audit 已从“返回安全 locator”继续推进到“next_actions 也返回安全 locator 摘要”。
- 新增 `_format_agent_context_locator`，只格式化 `id`、`agent_session_id`、`status`、`context_summary_chars`，不读取、不拼接、不返回 raw `context_summary`。
- Admin/API 与 CLI production readiness 在出现 over-budget、redacted、sensitive-looking agent context 时，会追加 latest locator next action，运营可以定位要清理的 session，但不需要读取 summary 文本。
- 本切片不改变交易 API、模型调用、handoff enablement 或订单执行；外部订单后端仍 disabled-by-default。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `backend/services/ai_trading_production_readiness_service.py`
  - 新增 `_format_agent_context_locator`。
  - over-budget summary blocker 的 next action 追加 latest over-budget locator。
  - redacted/sensitive warning 的 next action 追加 latest redacted/sensitive locator。
  - locator 只包含非敏感定位字段，不包含 summary、token、API key、DB URL 或 downstream response body。
- `backend/tests/test_ai_trading_production_readiness_api.py`
  - 覆盖 Admin readiness API 的 locator next actions。
  - 断言 over-budget/redacted/sensitive actions 带 session/status/chars，并且 fake secret 不会出现在响应中。
- `backend/tests/test_ai_trading_production_readiness_check.py`
  - 覆盖 CLI `--include-db-audits` 的 over-budget locator next action。
  - DB-audit fail-closed 测试的假 password fixture 改为分段拼接，避免静态 secret scan 把测试文本误判为泄露。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 progress marker、focused/aggregate/one-key 验收证据。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 locator next actions 覆盖范围和最新一键验收编号。

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_production_readiness_service.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_production_readiness_check.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_api.py::test_admin_readiness_reports_agent_session_context_budget_without_summary_leakage tests/test_ai_trading_production_readiness_check.py::test_include_db_audits_adds_handoff_and_agent_context_gates_without_secret_leakage tests/test_ai_trading_production_readiness_check.py::test_include_db_audits_fails_closed_without_leaking_database_error_text -q`：3 passed，1 个既有 UTC deprecation warning。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：78 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、78 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local/production completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- 最新一键验收 live mock handoff 证据：strategy spec `#60`、signal event `#58`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=45`、`handoff_attempts.total=56`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- 生产实盘切换仍需要外部 evidence 文件位于 repo 外或私有 ops evidence 位置，并通过 completion audit 的 schema、secret、timestamp、artifact-ref 和 text-quality gate。
- 真实 admin 登录态 visual acceptance 仍未完成；本地 auth disabled 时 Admin readiness 控件隐藏是预期状态。
