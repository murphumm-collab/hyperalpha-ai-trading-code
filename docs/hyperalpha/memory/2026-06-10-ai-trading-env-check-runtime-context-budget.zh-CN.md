# 2026-06-10 AI Trading Env Check Runtime Context Budget Gate

## 压缩记忆

- 本地切片：把 runtime agent-session context budget 纳入 `ai_trading_v1_env_check.py --strict`。
- 目标是让一键本地 V1 验收不只是“看到” `/api/ai-trading/runtime` 的 `agent_sessions.context_budget`，而是明确要求该字段存在且保持 counts-only secret policy。
- `build_report` 现在在 backend runtime check 中输出 `runtime_agent_context_budget`，并在 runtime 缺少 `agent_sessions.context_budget` 时加入 `backend_agent_context_budget_missing` blocker。
- 如果 `runtime_agent_context_budget.secret_policy != counts_only_no_summary_text`，env-check 会加入 `backend_agent_context_budget_secret_policy_invalid` blocker，避免 stale/错误后端把 raw context summary 当成 readiness 通过。
- 本切片不改变交易 API、模型 provider、handoff enablement 或订单执行；外部订单后端仍 disabled-by-default。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `backend/scripts/ai_trading_v1_env_check.py`
  - 提取 runtime `agent_sessions.context_budget` 到 `checks.backend_8802.runtime_agent_context_budget`。
  - 新增缺 budget blocker 和 secret policy regression blocker。
  - 新增对应 `next_actions`，提示重启/同步 backend 或保持 counts-only budget contract。
- `backend/tests/test_ai_trading_env_check.py`
  - ready fixture 默认带 counts-only `runtime_agent_context_budget`。
  - 新增 missing budget 和 invalid secret policy 两个 fail-closed tests。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新一键验收到 82 条回归。
  - 更新 latest live mock handoff evidence：strategy spec `#63`、signal event `#61`、handoff attempts `59`。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 `AI Trading env-check runtime context budget gate` Done 标记。
  - 记录 focused env-check、aggregate regression 和 one-key local acceptance evidence。

## 已验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_env_check.py tests/test_ai_trading_env_check.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py -q`：6 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：82 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、82 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local/production completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- 一键验收 runtime readiness 输出包含 `runtime_agent_context_budget.secret_policy=counts_only_no_summary_text`、`total=48`、`active=47`、`redacted_context_summary_count=1`、`over_budget_count=0`，且不返回 summary 原文。
- 最新一键验收 live mock handoff 证据：strategy spec `#63`、signal event `#61`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=48`、`handoff_attempts.total=59`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。
- `scripts/local-dev/install_launch_agent.sh` 已再次同步 runtime mirror；随后 `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict` 返回 `ready=true`，latest running runtime 显示 `runtime_agent_context_budget.secret_policy=counts_only_no_summary_text`、`total=49`、`active=48`、`archived=1`、`redacted_context_summary_count=1`、`over_budget_count=0`。

## 下一步注意

- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- 真实模型调用仍需要用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需要真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
- 实际 macOS 整机重启恢复、真实 admin visual、真实生产登录态 session detail、真实 exchange execution 仍是外部验收项。
