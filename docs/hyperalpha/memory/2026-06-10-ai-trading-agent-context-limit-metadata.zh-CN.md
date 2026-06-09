# 2026-06-10 AI Trading Agent Context Limit Metadata Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading agent session context/compression packet 现在显式暴露请求上限、最大上限和摘要字符上限。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- Backend context limits：
  - 新增服务常量：
    - `AGENT_CONTEXT_SUMMARY_MAX_CHARS = 2000`
    - `AGENT_CONTEXT_STRATEGY_MAX_LIMIT = 20`
    - `AGENT_CONTEXT_SIGNAL_MAX_LIMIT = 50`
    - `AGENT_CONTEXT_ATTEMPT_MAX_LIMIT = 100`
  - `_clean_agent_context_summary` 使用 `AGENT_CONTEXT_SUMMARY_MAX_CHARS`，保持摘要长度上限和敏感关键词红线脱敏。
  - Agent session context packet 的 `compression` metadata 新增：
    - `strategy_requested_limit`
    - `signal_requested_limit`
    - `attempt_requested_limit`
    - `strategy_max_limit`
    - `signal_max_limit`
    - `attempt_max_limit`
    - `summary_max_chars`
  - 原有 `strategy_limit` / `signal_limit` / `attempt_limit` 字段继续表示实际返回数量，保持前端兼容。
  - API route 的 `Query(..., le=...)` 改为使用服务常量，避免路由和服务上限漂移。

- 测试：
  - Route regression 断言 context packet 返回 requested/effective/max limits 和 `summary_max_chars=2000`。
  - Route regression 断言压缩摘要长度不超过 `summary_max_chars`。
  - Route regression 断言 over-limit context/compress 请求返回 422。

## 已验证

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：35 passed。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：59 passed，4 个既有 UTC deprecation warnings。

## 下一步注意

- 这些 limits 是本地/后端 context packet 的安全边界；真实 DeepSeek/Qwen live acceptance 仍需要真实用户 Hyper AI profile/API key。
- 后续如提高 limits，应同步评估单服务器共享模型并发、prompt token 成本和 response latency。
