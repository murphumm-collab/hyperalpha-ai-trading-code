# 2026-06-10 AI Trading Model Adjust Context Budget Audit Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading DeepSeek/Qwen model-adjust 的 agent session context 审计现在包含摘要长度和最大字符上限。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- Backend：
  - `_build_model_adjustment_agent_context` 返回：
    - `context_summary_chars`
    - `summary_max_chars`
  - `summary_max_chars` 使用同一个 `AGENT_CONTEXT_SUMMARY_MAX_CHARS = 2000` 服务常量。
  - 正常摘要和 `[redacted_sensitive_context]` 都会带字符计数，方便审计 DeepSeek/Qwen prompt context budget。
  - 不返回 API key、profile key、session secret、gateway URL、authorization 或 token。

- 测试：
  - Saved-spec model-adjust 精确断言 `context_summary_chars` 和 `summary_max_chars=2000`。
  - Unsaved sensitive context model-adjust 断言 redacted summary 的字符计数和上限。
  - Saved sensitive context model-adjust 断言 redacted summary 的字符计数和上限。
  - 原有 prompt/body/response secret leakage 断言继续保留。

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：35 passed。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：59 passed，4 个既有 UTC deprecation warnings。

## 下一步注意

- 这只是审计字段，不会触发真实模型调用；真实 DeepSeek/Qwen live acceptance 仍需要用户 Hyper AI profile/API key 和显式 `--confirm-live-model-call`。
- AI 仍是 signal-only，不会直接下单。
