# 2026-06-12 context compression prompt 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的安全多用户 Agent 底座。
- 上一轮已收紧 context compression failure logs；本轮继续收紧同一共享压缩链路的模型输入边界：旧消息、tool_result、tool name 中的 API key、token、Bearer、private key、authorization、DB URL 等 secret-like 内容不能进入 summary LLM request body。

## 已完成

- `backend/services/ai_context_compression_service.py`
  - 新增 `_redact_sensitive_text_for_compression_prompt` 和 compression prompt 专用敏感模式。
  - 普通 message content 进入 `COMPRESSION_PROMPT` 前会先脱敏。
  - Anthropic `tool_use.name`、`tool_result.content` 进入压缩 prompt 前会先脱敏。
  - OpenAI `tool_calls[].function.name` 进入压缩 prompt 前会先脱敏。
  - 保留非敏感 tool name，例如 `safe_market_scan`，不影响正常压缩摘要上下文。
- `backend/tests/test_ai_context_compression_error_safety.py`
  - 新增 provider request body 捕获测试，证明 secret-like user message/tool content 不会发送给 summary LLM，安全 tool name 仍保留。
  - 既有 provider failure/connection/background failure/source guard 继续覆盖。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - status marker requirement 新增 `AI Trading context compression prompt safety`。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 与 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker，并把 focused verification 更新为 error/prompt safety 6 passing tests。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新本轮 focused safety 验收证据。

## 验证

- `cd backend && uv run python -m py_compile services/ai_context_compression_service.py tests/test_ai_context_compression_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_context_compression_error_safety.py -q`：6 passed。
- `cd backend && uv run pytest tests/test_ai_context_compression_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "context_compression_error_safety or context_compression_prompt_safety or current_repo_completion_audit"`：通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、当前分支 `codex/ai-agent-multitenant-foundation`、无 local blockers。
- `scripts/local-dev/install_launch_agent.sh` 后，`cd backend && AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`：第二次通过，backend/frontend/mock gateway ready，`runtime_mirror.current=true`，gateway `target_kind=local_mock`，`ready=true`，实盘 handoff 仍未批准。
- Source guard：`ai_context_compression_service.py` 不再保留 compression failure path 的 raw `response.text`、response snippet、endpoint metadata、`{e}` exception text 或 `type(e).__name__` patterns，并且 prompt builder 不再直接把 raw `content` / tool result 写入 `conv_parts`。

## 未改变

- 没有启用真实订单后端 handoff。
- 没有调用真实 DeepSeek/Qwen API。
- 没有改变 signal-only/no-direct-order/backtest gate/user confirmation/hard-risk 边界。
- 没有合并分支。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮提交后继续只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 一键验收标准仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen 和生产审批 evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。
