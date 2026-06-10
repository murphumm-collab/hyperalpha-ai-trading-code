# 2026-06-10 AI Trading Production Evidence Explain Gate

## 压缩记忆

- 本地切片：把 `ai_trading_v1_completion_audit.py --explain-production-evidence` 纳入一键本地 V1 验收门禁，避免 explain mode 只存在但没有被 aggregate acceptance 跑到。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 新增 `Production evidence explain mode gate`。
- 新 gate 会运行 explain mode，并断言：`mode=production_evidence_explain`、`local_v1_accepted=true`、`ready_for_live_orders=false`、`production_evidence.ready=false`、未提供外部 evidence、7 个外部验收 item id 完整、安全 artifact-ref scheme、required item fields、`real_order_backend_handoff` 有 `external_evidence_item_not_provided` blocker、forbidden values 和 operator guidance 存在。
- `backend/scripts/ai_trading_v1_completion_audit.py` 的 local requirement 现在要求一键验收脚本包含 `Production evidence explain mode gate`、`--explain-production-evidence`、`production_evidence_explain_gate`；如果有人从 runner 中删除该 gate，strict-local 会 fail closed。
- `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺失 explain gate 时 local V1 不 accepted 的回归。
- GitHub 上传：按用户要求跳过；本轮只在 `codex/ai-agent-multitenant-foundation` 做本地开发、测试、验收标记和本地 commit，不 push、不 merge。
- default production readiness DB-audit blocker 仍在一键验收中被覆盖，避免把本地 mock V1 误判为 production ready。
- 继续保留 local V1 边界：`ready_for_live_orders=false`，真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是外部验收 blocker。

## 变更文件

- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - usage 增加 production evidence explain mode gate。
  - 新增 `run_production_evidence_explain_gate`。
  - 在 production completion boundary expected blocker 之后、production evidence initializer gate 之前执行 explain gate。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - aggregate runner requirement 要求 explain gate 相关短语。
  - status gate 标题推进到 `Local V1 Production Evidence Explain Gate Accepted / Remote Push Skipped`。
  - status gate 要求 `AI Trading aggregate production evidence explain gate` Done 标记。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal fixture 增加 explain gate 文本。
  - 新增 `test_completion_audit_blocks_local_acceptance_when_explain_gate_is_missing`。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 一键验收覆盖项新增 production evidence explain mode gate。
  - 聚合回归预期更新到 95 条。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 当前状态更新为 production evidence explain gate accepted。
  - 增加 scope 和 Done marker。
- `docs/hyperalpha/memory/latest.md`
  - 指向本文件。

## 已验证

- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：passed。
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：23 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed；报告 `local_v1_accepted=true`、`local_blockers=[]`、`github_upload=deferred_by_user_request`、`ready_for_live_orders=false`、`production_track=pending_external_acceptance`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：95 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、95 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local completion summary gate、production completion boundary expected blocker、production evidence explain mode gate、production evidence initializer gate、production evidence template expected blocker、frontend build、local LaunchAgent runtime sync、runtime readiness freshness/cold-start retry、live local mock handoff。
- 最新一键验收 runtime readiness：attempt 1/2 为 LaunchAgent 冷启动等待，attempt 3 `ready=true`、`blockers=[]`、`runtime_mirror.current=true`、`secret_policy=metadata_only_no_env_or_credentials`。
- 最新一键验收 live mock handoff evidence：strategy spec `#77`、signal event `#75`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=62`、`handoff_attempts.total=73`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- commit 后要重跑 `scripts/local-dev/install_launch_agent.sh`，让 runtime mirror metadata 的 `source_git_commit` 指向新提交。
- 真实 production evidence 未完成前，completion audit 的 `ready_for_live_orders=false` 必须保持。
- 真实 production evidence 必须放在仓库外或私有 ops evidence 位置；repo 内 template 不能解锁 live ready。
- 真实模型调用仍需用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
- 实际 macOS 整机重启恢复、真实 admin visual、真实生产登录态 session detail、真实 exchange execution 仍是外部验收项。
