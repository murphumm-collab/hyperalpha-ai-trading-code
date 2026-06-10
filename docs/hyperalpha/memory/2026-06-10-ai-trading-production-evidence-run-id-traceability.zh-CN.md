# AI Trading Production Evidence Run ID Traceability 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence 在 `evidence_run_id` 基础上新增 traceability 防护：root `cutover_approval_ref` 和每个 item 的 `artifact_refs` 必须包含同一个 root `evidence_run_id`。
- Completion audit 新增 `external_evidence_cutover_approval_ref_missing_run_id` 与 `external_evidence_artifact_ref_missing_run_id` blocker，避免复制旧审批/旧 artifact refs 后只改时间或 run id 来凑生产 evidence。
- Production evidence template 与 explain schema 更新：`evidence_run_id` 不只是存在，还必须能追踪到审批引用和每项验收 artifact。
- Completion audit 本地验收新增 marker：`| AI Trading production evidence run id traceability | Done |`，缺失时本地 V1 不会被接受。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- Production evidence template note max length：281 chars，仍满足 note bounds gate。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：79 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：150 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`，`ready_for_live_orders=false`，`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 150 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。runtime readiness attempts 1-2 是正常冷启动等待，attempt 3 `ready=true`、`runtime_mirror.current=true`、`runtime_gateway.mode=http`、`target_kind=local_mock`。最新 local/mock 证据为 spec `#105`、signal event `#103`、gateway response `mock_accepted`、`agent_sessions.total=91`、`handoff_attempts.total=101`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成、缺少 `evidence_run_id`、`cutover_approval_ref` 或任意 item `artifact_refs` 未包含同一个 `evidence_run_id`、缺少审批引用、没有 `cutover_window.start_at/end_at`、切换窗口不包含生产审计时间、切换窗口超过 8 小时、evidence 过期、有效期超过 7 天、root/item 时间戳超过当前时间 300 秒以上、或 item `validated_at` 比 root `generated_at` 早超过 7 天时，`ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
