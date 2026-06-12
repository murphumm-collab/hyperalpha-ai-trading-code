# 2026-06-12 Hyper AI service stream 错误输出安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的安全多用户 Agent 底座。
- 上一轮已修 Hyper AI direct tool/dispatcher 错误输出；本轮继续收窄 Hyper AI service 本身的 chat/insight/onboarding/model-test failure paths，避免 raw provider body、request exception、parser exception、URL、secret-like values 或 `str(e)` 写入 SSE、用户可见错误或 Agent conversation。

## 已完成

- `backend/services/hyper_ai_service.py`
  - 新增固定安全错误常量与 `_safe_hyper_ai_error_event` / `_safe_hyper_ai_provider_failure_event` / `_safe_hyper_ai_parse_failure_event`。
  - `test_llm_connection` 失败不再返回 provider response body 或 request exception text，只返回固定安全 message/error_code/status。
  - 主 `stream_chat_response` provider failure 不再拼接 `response.text` / request exception 到 `assistant_msg.content`、`interrupt_reason`、SSE `interrupted.error` 或 SSE `error.message`。
  - 主 chat parse failure 不再返回 parser exception text。
  - 主 chat outer exception 不再把 `str(e)` 写入 assistant message 或 SSE。
  - `stream_insight_response` provider failure / stream exception 改为固定安全 SSE error。
  - onboarding stream outer exception 改为固定安全 SSE error。
  - suggestions 相关日志不再打印 provider response body、connection exception、JSON parse exception 或 unexpected exception text。
- `backend/tests/test_hyper_ai_service_error_safety.py`
  - 新增 LLM connection test provider-body redaction、Insight stream provider failure redaction、source guard。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 与 AI Trading backend regression 纳入 `services/hyper_ai_service.py` / `tests/test_hyper_ai_service_error_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - local acceptance runner requirement 纳入 `tests/test_hyper_ai_service_error_safety.py`。
  - status marker requirement 新增 `AI Trading Hyper AI service stream error safety`。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo 与 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Scope bullet、Done marker 和 focused verification evidence。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 新增本轮 focused safety 验收证据。

## 验证

- `cd backend && uv run python -m py_compile services/hyper_ai_service.py tests/test_hyper_ai_service_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_service_error_safety.py -q`：3 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_service_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_service_stream_error_safety or hyper_ai_service_error_safety or current_repo_completion_audit"`：5 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、当前分支 `codex/ai-agent-multitenant-foundation`、无 local blockers。
- Source guard：`hyper_ai_service.py` 不再保留 Hyper AI SSE/API failure path 的 raw `str(e)`、parser exception text、provider `response.text`、`last_response_text` 或 raw interruption message pattern。

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
