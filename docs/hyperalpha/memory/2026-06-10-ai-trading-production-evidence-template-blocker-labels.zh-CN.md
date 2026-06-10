# AI Trading Production Evidence Template Blocker Labels 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Settings/Admin production evidence blocker formatter 现在显式覆盖模板默认 dry-run 会出现的缺项 blocker：`external_evidence_cutover_window_start_at_missing`、`external_evidence_cutover_window_end_at_missing`、`external_evidence_summary_missing`、`external_evidence_validated_by_missing`。
- Frontend source guard 新增这些模板 blocker 的标签检查，避免管理员第一次加载 pending template 后看到 fallback 文案或原始 blocker id。
- Completion audit 新增 `| AI Trading production evidence template blocker labels | Done |` gate；缺少该标记时本地 V1 完成度审计会失败。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：74 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：159 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`，`ready_for_live_orders=false`，`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 159 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#110`、signal event `#108`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=96`、`handoff_attempts.total=106`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- 本轮只增强 production evidence 模板 blocker 的管理员可读性，不改变 `ready_for_live_orders=false` 的默认生产边界。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
