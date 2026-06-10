# AI Trading Production Evidence Validation Guidance 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Admin production evidence dry-run validation API 现在随 `validation` 一起返回非敏感 `guidance`，复用 template guidance 的 item guidance、required summary terms、safe artifact schemes、forbidden value labels 和 next-required actions。
- Settings/Admin 在 Validate 后会刷新 Template guidance，并在 blocked evidence item 上显示安全的 `Missing terms` 与首条 `Fix` 指导；不渲染 evidence file path、API key、token、订单后端 URL 或原始 evidence summary。
- Completion audit 新增 `| AI Trading production evidence validation guidance | Done |` gate，防止 status 文档遗漏该验收标记。

## 当前验证状态

- py_compile 已通过。
- 首次 focused pytest 失败符合预期：新 completion gate 生效但 status/checklist/memory 尚未补齐；补齐后复跑通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py -q`：95 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：166 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，剩余为既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker 按预期阻断、runtime mirror 冷启动重试和 live local mock handoff；最新证据为 strategy spec `#116`、signal event `#114`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=102`、`handoff_attempts.total=112`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮不改变 `ready_for_live_orders=false` 默认生产边界。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
