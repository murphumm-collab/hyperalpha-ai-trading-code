# 2026-06-10 AI Trading Production Evidence Explain Mode

## 压缩记忆

- 本地切片：给 `backend/scripts/ai_trading_v1_completion_audit.py` 增加 `--explain-production-evidence`，把外部 production evidence 从纯 blocker JSON 扩展成逐项、非敏感、可操作的验收清单。
- explain mode 不访问模型、交易所、GitHub 或订单后端；它只读取本地文档、Git metadata 和可选 production evidence JSON。
- 输出 `mode=production_evidence_explain`，包含 `local_v1_accepted`、`ready_for_live_orders`、`production_track`、production evidence summary、schema 限制、7 个外部验收项的 required fields、safe artifact-ref schemes、forbidden values、operator guidance 和当前 blockers。
- 未提供外部 evidence 时，每个外部验收项返回 `external_evidence_item_not_provided`；提供完整 evidence 但未显式 `--allow-live-ready-from-evidence` 时，production evidence 可为 ready，但 `ready_for_live_orders=false` 仍保持。
- completion audit 现在要求 status 文档保留 `AI Trading production evidence explain mode` Done 标记和 `Local V1 Production Evidence Explain Mode Accepted / Remote Push Skipped` 状态标题。
- GitHub 上传：按用户要求跳过；本轮只在 `codex/ai-agent-multitenant-foundation` 做本地开发、测试、验收标记和本地 commit，不 push、不 merge。
- default production readiness DB-audit blocker 仍在一键验收中被覆盖，避免把本地 mock V1 误判为 production ready。
- 继续保留 local V1 边界：`ready_for_live_orders=false`，真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是外部验收 blocker。

## 变更文件

- `backend/scripts/ai_trading_v1_completion_audit.py`
  - 新增 production evidence required fields / forbidden values / item guidance 常量。
  - 新增 `build_production_evidence_explain(...)`。
  - CLI 新增 `--explain-production-evidence`。
  - strict-local status gate 要求 production evidence explain mode Done 标记。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - 新增 3 条 explain mode 回归：缺 evidence 的 item-level blocker、完整 evidence 但未显式 cutover 仍阻断 live orders、CLI 输出非敏感 checklist。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 增加 `--explain-production-evidence` 验收命令说明。
  - 更新聚合回归到 94 条，最新 live mock handoff evidence 为 spec `#76`、signal event `#74`、`agent_sessions.total=61`、`handoff_attempts.total=72`。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 当前状态更新为 production evidence explain mode accepted。
  - 增加 scope、Done marker 和验证日志。
- `docs/hyperalpha/memory/latest.md`
  - 指向本文件。

## 已验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：22 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --explain-production-evidence`：返回 `mode=production_evidence_explain`、`local_v1_accepted=true`、`ready_for_live_orders=false`、`production_evidence.ready=false`、7 个外部验收项，且 `real_order_backend_handoff` blocker 为 `external_evidence_item_not_provided`。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed；报告 `local_v1_accepted=true`、`local_blockers=[]`、`github_upload=deferred_by_user_request`、`ready_for_live_orders=false`、`production_track=pending_external_acceptance`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：94 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、94 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local completion summary gate、production completion boundary expected blocker、production evidence initializer gate、production evidence template expected blocker、frontend build、local LaunchAgent runtime sync、runtime readiness freshness/cold-start retry、live local mock handoff。
- 最新一键验收 runtime readiness：attempt 1/2 为 LaunchAgent 冷启动等待，attempt 3 `ready=true`、`blockers=[]`、`runtime_mirror.current=true`、`secret_policy=metadata_only_no_env_or_credentials`。
- 最新一键验收 live mock handoff evidence：strategy spec `#76`、signal event `#74`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=61`、`handoff_attempts.total=72`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 新增 tracked 文件后，需要先纳入 Git index 再做最终 runtime sync，否则 `git ls-files` digest 不会包含未跟踪文件。
- commit 后要重跑 `scripts/local-dev/install_launch_agent.sh`，让 runtime mirror metadata 的 `source_git_commit` 指向新提交。
- 真实 production evidence 未完成前，completion audit 的 `ready_for_live_orders=false` 必须保持。
- 真实 production evidence 必须放在仓库外或私有 ops evidence 位置；repo 内 template 不能解锁 live ready。
- 真实模型调用仍需用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
- 实际 macOS 整机重启恢复、真实 admin visual、真实生产登录态 session detail、真实 exchange execution 仍是外部验收项。
