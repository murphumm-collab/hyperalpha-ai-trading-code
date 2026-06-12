# 2026-06-13 Hyper AI suggestions context 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 上一轮已收紧 Hyper AI profile preference/onboarding 字段，避免 profile 字段进入 `/profile`、system prompt、suggestions prompt 时泄漏 secret-like 文本。
- 本轮补齐 suggested questions 的 conversation context 边界：最近会话标题和 message snippets 会被拼进 suggested-question LLM prompt，不能让用户误贴的 API key、token、Bearer、private key、password、DB URL 或 `sk-*` key 通过隐藏二次 LLM 调用或侧边栏标题泄漏。

## 已完成

- `backend/services/hyper_ai_service.py`
  - 新增 `REDACTED_SENSITIVE_CONVERSATION_TEXT`、`sanitize_conversation_text_for_response`、`build_safe_conversation_title`。
  - profile/conversation secret-like pattern 扩展覆盖 `sk-*` key。
  - `save_message` 自动生成 conversation title 时先脱敏；secret-like first user message 只生成固定 redaction title。
  - `get_suggestions_context` 对 legacy/polluted conversation title 和 recent message snippets 脱敏后再返回。
  - `build_suggestions_prompt` 再次清洗传入的 conversation title/snippets，避免未来调用方绕过 `get_suggestions_context`。
  - suggestions LLM 调用日志不再记录 raw endpoint；缓存更新日志不再记录 generated questions 原文。
- `backend/api/hyper_ai_routes.py`
  - `/api/hyper-ai/conversations` 对 legacy/polluted title 做响应层脱敏，避免侧边栏直接渲染 secret-like title。
- `backend/tests/test_hyper_ai_suggestions_context_safety.py`
  - 新增 first user message secret-like title redaction regression。
  - 新增 legacy polluted title/snippet 在 conversation API、suggestions context、suggestions prompt 中脱敏的 regression。
  - 新增 `build_suggestions_prompt` 对外部 context 再清洗的 regression。
  - 新增 source guard 防止 raw title/snippet/prompt/log patterns 回归。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 和 AI Trading backend regression test list 纳入 `tests/test_hyper_ai_suggestions_context_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - aggregate runner required phrases 纳入 `tests/test_hyper_ai_suggestions_context_safety.py`。
  - completion audit 新增 `AI Trading Hyper AI suggestions context safety` required marker。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 和 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker 和 focused verification。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 focused suggestions context safety 证据。

## 验证

- `cd backend && uv run python -m py_compile api/hyper_ai_routes.py services/hyper_ai_service.py tests/test_hyper_ai_suggestions_context_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_suggestions_context_safety.py -q`：4 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_suggestions_context_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_suggestions_context_safety or current_repo_completion_audit"`：6 passed, 159 deselected。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、current branch `codex/ai-agent-multitenant-foundation`、无 local blockers、production evidence 仍 pending。

## 未改变

- 没有启用真实订单后端 handoff。
- 没有调用真实 DeepSeek/Qwen API。
- 没有改变用户可见 chat message 存储；本轮只处理自动标题、conversation list title、suggested-question context/prompt 和 suggestions 日志。
- 没有改变 signal-only/no-direct-order/backtest gate/user confirmation/hard-risk 边界。
- 没有合并分支。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮提交后继续只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 完成度仍以 strict-local completion audit 和一键本地 acceptance runner 为准；完整一键命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen profile/API key 和生产审批 evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。
