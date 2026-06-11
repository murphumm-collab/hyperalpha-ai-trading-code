# AI Trading Production Evidence Dry-Run Safety Metadata 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Admin `/api/ai-trading/admin/production-evidence-validate` 返回非敏感 `dry_run` 元数据，明确该请求只做 `admin_payload_validation_only`，输入只接受 JSON object，`persistence=not_stored`，不会调用模型、交易所、订单后端、GitHub 或外部网络，也不会解锁 live orders。
- `dry_run` 只返回 payload byte count、max payload bytes、item key count、max item keys、固定调用边界和 secret policy，不返回 evidence 原文、文件路径、API key、token、订单后端 URL、raw evidence summary 或原始日志。
- Settings/Admin Production Evidence dry-run validation UI 新增 Dry-run safety 面板，显示 payload/item-key bounds、not-stored persistence、live-order blocked 状态、no network/model/order-backend/exchange/GitHub calls 和 metadata-only secret policy。
- Completion audit 新增 `| AI Trading production evidence dry-run safety metadata | Done |` gate，并把本地验收标题推进到 `Local V1 Evidence Dry-Run Safety Metadata Accepted / Remote Push Skipped`，防止 Admin dry-run 的“不持久化/不下单/不外呼”边界只存在于代码里而没有验收标记。

## 当前验证状态

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py -q`：99 条通过，保留 14 条既有 UTC deprecation warnings；第一次 focused run 在 status marker 未补齐时失败，证明 completion audit 会阻断缺少 dry-run safety marker 的状态。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：170 条通过，保留 14 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，剩余为既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker 按预期阻断、runtime mirror 冷启动重试和 live local mock handoff；runtime readiness 第 3 次恢复为 `ready=true`，最新证据为 strategy spec `#120`、signal event `#118`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=106`、`handoff_attempts.total=116`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮不改变生产实盘边界，不触发真实模型调用、真实订单后端 handoff、真实交易所执行、GitHub 上传或 production evidence 持久化。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
