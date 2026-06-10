# 2026-06-10 AI Trading Runtime Mirror Freshness

## 压缩记忆

- 本地切片：让一键本地 V1 验收确认 LaunchAgent runtime mirror 跑的是当前代码，而不是旧同步副本。
- `scripts/local-dev/install_launch_agent.sh` 现在会在 runtime mirror 根目录写 `.hyperalpha-runtime-sync.json`，记录 `version`、source/runtime root、source branch、source commit、source tree digest、sync time。
- runtime sync metadata 是 metadata-only：不写 env、API key、token、authorization、private key、password 或其它凭据。
- `backend/scripts/ai_trading_v1_env_check.py` 新增 `--repo-root`、`--runtime-root`、`--require-runtime-mirror-current`，会用 Git tracked source tree digest 对比 runtime metadata；metadata 缺失、JSON 无效、版本错误、digest 缺失、无法计算 source digest 或 digest mismatch 都会 fail closed。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 现在在 frontend build 后先执行 `Local LaunchAgent runtime sync`，再用 `run_runtime_readiness_with_retry` 跑 `ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`，最多 12 次，每次间隔 5 秒，处理 backend/frontend/mock gateway 冷启动。
- completion audit 现在要求一键验收脚本包含 `Local LaunchAgent runtime sync`、`scripts/local-dev/install_launch_agent.sh`、`--require-runtime-mirror-current`、`Runtime readiness attempt`、`run_runtime_readiness_with_retry`，并要求 status 文档保留 `AI Trading runtime mirror freshness gate` / `AI Trading runtime readiness cold-start retry` Done 标记。
- GitHub 上传：按用户要求跳过；本轮只在 `codex/ai-agent-multitenant-foundation` 做本地开发、测试、验收标记和本地 commit，不 push、不 merge。
- default production readiness DB-audit blocker 仍在一键验收中被覆盖，避免把本地 mock V1 误判为 production ready。
- 继续保留 local V1 边界：`ready_for_live_orders=false`，真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是外部验收 blocker。

## 变更文件

- `scripts/local-dev/install_launch_agent.sh`
  - 新增 source tree digest 计算和 `.hyperalpha-runtime-sync.json` 写入。
  - 元数据只记录分支、commit、digest 和同步时间，不记录 secret。
- `backend/scripts/ai_trading_v1_env_check.py`
  - 新增 runtime mirror freshness report。
  - 新增 `--require-runtime-mirror-current` fail-closed gate。
  - `next_actions` 会在 mirror stale/missing 时提示重跑 `scripts/local-dev/install_launch_agent.sh`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - 新增 `Local LaunchAgent runtime sync` step。
  - 新增 `run_runtime_readiness_with_retry`，避免 LaunchAgent 刚重启时的短暂 false negative。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - 本地完成度审计要求 one-key runner 和 status 文档包含 runtime mirror freshness/cold-start retry gate。
- `backend/tests/test_ai_trading_env_check.py`
  - 覆盖 metadata digest match 时 ready。
  - 覆盖 required mirror freshness 且 digest mismatch 时 blocker 为 `runtime_mirror_source_tree_digest_mismatch`。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal fixture 加入 runtime mirror gate 短语和 Done 标记。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 最新本地验收证据更新到 90 regressions、strategy spec `#74`、signal event `#72`、`agent_sessions.total=59`、`handoff_attempts.total=70`。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 当前状态更新为 runtime mirror freshness gate accepted，并补充验证日志。

## 已验证

- `bash -n scripts/local-dev/install_launch_agent.sh scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：passed。
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_env_check.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_v1_completion_audit.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_v1_completion_audit.py -q`：27 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed；`local_v1_accepted=true`、`local_blockers=[]`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：90 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、90 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local completion summary gate、production completion boundary expected blocker、production evidence initializer gate、production evidence template expected blocker、frontend build、local LaunchAgent runtime sync、runtime readiness freshness gate、live local mock handoff。
- 最新一键验收 runtime readiness：attempt 1/2 为 LaunchAgent 冷启动等待，attempt 3 `ready=true`、`blockers=[]`、`runtime_mirror.current=true`、`secret_policy=metadata_only_no_env_or_credentials`。
- 最新一键验收 live mock handoff evidence：strategy spec `#74`、signal event `#72`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=59`、`handoff_attempts.total=70`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 后续每次改代码后，一键本地验收会自动同步 runtime mirror；如果只单独跑 env-check 且看到 `runtime_mirror_source_tree_digest_mismatch`，先重跑 `scripts/local-dev/install_launch_agent.sh`。
- 新增 tracked 文件后，需要先纳入 Git index 再做最终 runtime sync，否则 `git ls-files` digest 不会包含未跟踪文件。
- 真实 production evidence 未完成前，completion audit 的 `ready_for_live_orders=false` 必须保持。
- 真实模型调用仍需用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
- 实际 macOS 整机重启恢复、真实 admin visual、真实生产登录态 session detail、真实 exchange execution 仍是外部验收项。
