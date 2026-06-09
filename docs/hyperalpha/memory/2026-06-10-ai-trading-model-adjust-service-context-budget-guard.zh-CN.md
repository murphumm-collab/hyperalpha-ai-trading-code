# 2026-06-10 AI Trading Model Adjust Service Context Budget Guard

## 压缩记忆

- 本地切片：为 saved-spec DeepSeek/Qwen model-adjust 增加 service-layer context budget regression。
- 目标是防止内部调用绕过 FastAPI `context_summary` body limit 后，把超长 agent-session context 带进共享模型 prompt。
- 新测试直接调用 `save_strategy_spec_record` 保存 2000 字符以上的 agent context，再通过 saved-spec model-adjust route 走模型路径。
- 断言 `model_context.agent_session_context.context_summary` 被截断为 2000 字符、`context_summary_chars=2000`、`summary_max_chars=2000`，尾部哨兵不会出现在 API response 或模型 prompt 中。
- 本切片不改变交易 API、模型 provider、handoff enablement 或订单执行；外部订单后端仍 disabled-by-default。
- GitHub 上传：按用户要求跳过；本切片只做本地 commit，不 push、不 merge。
- 继续保留 local V1 边界：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 必须通过；default production readiness DB-audit blocker 必须仍在一键验收中被覆盖。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。

## 变更文件

- `backend/tests/test_ai_trading_routes.py`
  - 新增 `test_ai_trading_saved_model_adjustment_enforces_service_context_summary_budget`。
  - 通过 service save 绕过 API body limit，证明 service 层 `_clean_agent_context_summary` 的 2000 字符预算在 saved model-adjust prompt 构造前生效。
  - 断言模型 API key 不进入 prompt，尾部 `TAIL_SHOULD_NOT_REACH_MODEL` 不进入 prompt/response。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 `AI Trading model-adjust service context budget guard` Done 标记。
  - 记录 focused route、route suite、aggregate、one-key 验收证据。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 AI Trading 回归数量到 79，route regression 到 36，最新 live mock handoff 证据到 spec `#61` / signal event `#59`。

## 已验证

- `cd backend && uv run python -m py_compile tests/test_ai_trading_routes.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py::test_ai_trading_saved_model_adjustment_enforces_service_context_summary_budget -q`：1 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：36 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：79 passed，5 个既有 UTC deprecation warning。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；覆盖 backend compile、79 条 AI Trading 回归、API-level smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blocker、local/production completion boundary audits、production evidence template 预期阻断、frontend build、runtime readiness、live local mock handoff。
- 最新一键验收 live mock handoff 证据：strategy spec `#61`、signal event `#59`、gateway response `mock_accepted`、runtime `target_kind=local_mock`、`agent_sessions.total=46`、`handoff_attempts.total=57`、`model_adjustment.ready=false`，blocker 为 `model_profile_not_configured`。

## 下一步注意

- 本地 V1 accepted 不等于 production ready；真实 production evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- 真实模型调用仍需要用户 Hyper AI DeepSeek/Qwen profile/API key 和 `--confirm-live-model-call` 外部验收。
- 真实 production handoff 仍需要真实订单后端 URL/token、真实 Auth/JWKS、生产硬风控值和脱敏 evidence。
