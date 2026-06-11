# AI Trading Production Evidence Root Guidance 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Admin production evidence template guidance 新增非敏感 `root_fields`，覆盖 `version`、`evidence_run_id`、`generated_at`、`expires_at`、`cutover_window`、`cutover_approval_ref`、`secret_values_returned` 和 `notes` 的 required value、related blocker 与 operator guidance。
- Admin production evidence dry-run validation API 复用同一组 root-field guidance，让缺失 `evidence_run_id`、时间窗口、approval ref 或 secret boundary 的 blocker 可以直接映射到安全修复提示。
- Settings/Admin Production Evidence Template guidance 面板现在显示前 4 个 root-field rule 的字段名、必需值和首条 Fix hint；仍只渲染安全投影，不展示 evidence file path、API key、token、订单后端 URL、raw evidence summary 或原始日志。
- Completion audit 新增 `| AI Trading production evidence root guidance | Done |` gate，并把本地验收标题推进到 `Local V1 Evidence Root Guidance Accepted / Remote Push Skipped`，避免 status 文档漏记 root-level guidance。

## 当前验证状态

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- 首次 focused pytest 在 latest-memory 缺少一键验收命令原文时失败，证明 completion gate 会阻断不完整记忆；补齐后 `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py -q`：96 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：167 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，剩余为既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker 按预期阻断、runtime mirror 冷启动重试和 live local mock handoff；runtime readiness 第 10 次恢复为 `ready=true`，最新证据为 strategy spec `#117`、signal event `#115`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=103`、`handoff_attempts.total=113`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮不改变生产实盘边界，不触发真实模型调用、真实订单后端 handoff、真实交易所执行或 production evidence 持久化。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
