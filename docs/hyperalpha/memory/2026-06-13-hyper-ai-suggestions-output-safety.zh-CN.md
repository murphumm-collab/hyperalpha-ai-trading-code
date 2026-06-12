# 2026-06-13 Hyper AI suggestions output 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 上一轮已收紧 suggested questions 的 conversation context，避免会话标题和 snippets 把 secret-like 文本带进建议问题 LLM prompt。
- 本轮补齐 suggested questions 的输出边界：即使模型返回或历史缓存中出现 API key、token、Bearer、private key、password、DB URL、`sk-*` key 或超长文本，也不能直接缓存或返回到前端。

## 已完成

- `backend/services/hyper_ai_service.py`
  - 新增 `MAX_SUGGESTED_QUESTION_CHARS`。
  - 新增 `sanitize_suggested_question_for_response` 和 `sanitize_suggested_questions_for_response`。
  - `generate_suggested_questions` 对 LLM JSON array 输出先做 secret-like 过滤、空值过滤、去重和长度上限，再返回给缓存写入路径。
  - `get_or_update_suggestions` 读取历史 `profile.suggested_questions` cache 时也先做同样清洗，再返回给 API。
  - invalid response 日志改成固定 label，不再截取 raw model text。
  - suggestions cache 时间戳改用 timezone-aware UTC 生成后落回 naive UTC，避免新增 `utcnow()` deprecation warning。
- `backend/tests/test_hyper_ai_suggestions_context_safety.py`
  - 新增 output sanitizer regression，覆盖 secret-like output rejection、duplicate filtering 和 max-length bound。
  - 新增 cached suggestions API response sanitization regression。
  - 新增 generated suggestions path regression，通过 fake LLM response 证明 raw model output 被过滤后才返回。
  - source guard 防止 `return questions[:3]`、raw generated-question logging、raw invalid-response logging、raw cached JSON return 回归。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - completion audit 新增 `AI Trading Hyper AI suggestions output safety` required marker。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 和 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker 和 focused verification。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 focused suggestions output safety 证据。

## 验证

- `cd backend && uv run python -m py_compile services/hyper_ai_service.py tests/test_hyper_ai_suggestions_context_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_suggestions_context_safety.py -q`：7 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_suggestions_context_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_suggestions_output_safety or hyper_ai_suggestions_context_safety or current_repo_completion_audit"`：10 passed, 159 deselected。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、current branch `codex/ai-agent-multitenant-foundation`、无 local blockers、production evidence 仍 pending。

## 未改变

- 没有启用真实订单后端 handoff。
- 没有调用真实 DeepSeek/Qwen API。
- 没有改变 suggested-question prompt 生成入口；本轮只处理模型输出、缓存读出和相关日志。
- 没有改变 signal-only/no-direct-order/backtest gate/user confirmation/hard-risk 边界。
- 没有合并分支。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮提交后继续只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 完成度仍以 strict-local completion audit 和一键本地 acceptance runner 为准；完整一键命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen profile/API key 和生产审批 evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。
