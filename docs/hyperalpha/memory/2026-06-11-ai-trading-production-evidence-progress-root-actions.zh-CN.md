# AI Trading Production Evidence Progress Root Actions 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Completion audit 的 `progress` 安全投影新增 `root_next_required_actions`，把 root-level evidence blocker 转成运营可执行动作，覆盖 `evidence_run_id`、`generated_at`、`expires_at`、`cutover_window`、`cutover_approval_ref`、`contains_no_secrets`、`notes`、schema 和 repo-local evidence file blocker。
- Admin `/api/ai-trading/admin/production-evidence-explain` 与 `/api/ai-trading/admin/production-evidence-validate` 现在都会返回 `progress.root_next_required_actions`；未提供 evidence 时返回所有 root 修复动作，已接受的 sanitized evidence 返回空数组。
- Settings/Admin Production Evidence 的 explain/validation progress card 会显示 root-level actions，但仍只读取安全投影，不展示 evidence 文件路径、API key、token、订单后端 URL、raw evidence summary 或原始日志。
- Completion audit 新增 `| AI Trading production evidence progress root actions | Done |` gate，并把本地验收标题推进到 `Local V1 Evidence Progress Root Actions Accepted / Remote Push Skipped`，防止 progress summary/actions 只覆盖 item-level 而漏掉 root-level 修复动作。

## 当前验证状态

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py -q`：98 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：169 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，剩余为既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker 按预期阻断、runtime mirror 冷启动重试和 live local mock handoff；runtime readiness 第 3 次恢复为 `ready=true`，最新证据为 strategy spec `#119`、signal event `#117`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=105`、`handoff_attempts.total=115`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮不改变生产实盘边界，不触发真实模型调用、真实订单后端 handoff、真实交易所执行或 production evidence 持久化。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
