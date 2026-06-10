# AI Trading Production Evidence Artifact Ref Item Uniqueness 记忆

日期：2026-06-10
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Production evidence item `artifact_refs` 现在不能在同一个外部验收项内重复同一条 sanitized ref。
- Completion audit 新增 `external_evidence_artifact_ref_duplicate_in_item` blocker；重复 ref 即使包含正确的 `evidence_run_id` 和 item id，也不能用来凑满 1-5 条 artifact refs。
- Production evidence template、V1 checklist 和 status marker 均已同步为“不能 repeat 或 reuse refs”；本地完成度审计新增 `| AI Trading production evidence artifact ref item uniqueness | Done |` gate。
- 这轮规则与上一轮跨 item 去重组合后，真实生产 evidence 的每条 artifact ref 必须是脱敏、逐项、非重复的独立留痕。

## 验证结果

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- Production evidence template note max length：281 chars，仍满足 note bounds gate。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py -q`：85 passed，14 个既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：156 passed，14 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过；仅剩既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`，`ready_for_live_orders=false`，`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；覆盖 156 条 AI Trading 回归、frontend build、default production readiness DB-audit blocker、LaunchAgent runtime sync、runtime readiness 冷启动重试和 live local mock handoff。最新 local/mock 证据为 spec `#108`、signal event `#106`、gateway response `mock_accepted`、`agent_sessions.total=94`、`handoff_attempts.total=104`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 本地分支必须保持 `codex/ai-agent-multitenant-foundation`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是本地 V1 一键验收入口，并继续覆盖 default production readiness DB-audit blocker。
- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成、缺少 `evidence_run_id`、`cutover_approval_ref` 未包含 run id、任意 item `artifact_refs` 未同时包含同一个 `evidence_run_id` 和 item id、任意 artifact ref 在同一 item 内重复或跨 item 复用、缺少审批引用、没有 `cutover_window.start_at/end_at`、切换窗口不包含生产审计时间、切换窗口超过 8 小时、evidence 过期、有效期超过 7 天、root/item 时间戳超过当前时间 300 秒以上、或 item `validated_at` 比 root `generated_at` 早超过 7 天时，`ready_for_live_orders=false` 必须保持。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
- 生产切换 evidence 必须放在仓库外/private ops 位置，且不能包含 API keys、Bearer token、DB URL、private key、authorization header、原始模型输出或下单明文日志。
