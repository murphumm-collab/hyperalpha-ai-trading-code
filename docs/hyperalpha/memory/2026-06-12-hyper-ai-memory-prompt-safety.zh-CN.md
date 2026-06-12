# 2026-06-12 Hyper AI memory prompt 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 上一轮已收紧 context compression summary prompt；本轮收紧同一压缩链路里的 Hyper AI memory extraction/dedup prompt 与长期记忆写入边界。
- 目标是防止 API key、token、Bearer、authorization、private key、password、DB URL 等 secret-like 文本进入用户配置的 DeepSeek/Qwen extraction/dedup 请求，或被模型输出复述后写入长期记忆。

## 已完成

- `backend/services/hyper_ai_memory_service.py`
  - 新增 memory prompt/storage 专用 secret-like matcher。
  - `extract_memories_from_conversation` 会先脱敏 conversation text，再构造 extraction prompt。
  - extraction LLM 返回的 memory candidates 会在返回前过滤，secret-like content 不进入后续 dedup/storage。
  - `batch_dedup_memories` 会过滤 new memory candidates，脱敏 existing/new memory prompt 文本，再调用 dedup LLM。
  - dedup LLM 返回的 `merged` content 若含 secret-like 文本，会拒绝使用该 merge，改用原本已清洗的 safe content。
  - no-existing fallback 和 normal add/update paths 都只使用清洗后的 memory content。
- `backend/tests/test_hyper_ai_memory_error_safety.py`
  - 新增 extraction request body 捕获测试，证明 conversation secret-like 文本不会进入 provider request，且 secret-like extracted memory output 被过滤。
  - 新增 dedup request body 捕获测试，证明 legacy existing memory/new memory secret-like 文本不会进入 provider request，且 secret-like merge 不会写入 update。
  - source guard 防止 raw `conversation_text[:6000]`、raw memory content prompt 拼接、raw `merged` update 回归。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - completion audit 新增 `AI Trading Hyper AI memory prompt safety` required marker。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 和 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker，并把 focused memory safety 验证更新为 7 passing tests。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 focused memory error/prompt safety 证据。

## 验证

- `cd backend && uv run python -m py_compile services/hyper_ai_memory_service.py tests/test_hyper_ai_memory_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_memory_error_safety.py -q`：7 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_memory_error_safety or hyper_ai_memory_prompt_safety or current_repo_completion_audit"`：新 marker 加入文档前按预期失败，缺少 `| AI Trading Hyper AI memory prompt safety | Done |` 会让 local completion audit fail closed。
- 文档补齐 marker 和治理锚点后，`cd backend && uv run pytest tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_memory_error_safety or hyper_ai_memory_prompt_safety or current_repo_completion_audit"`：10 passed, 155 deselected。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、current branch `codex/ai-agent-multitenant-foundation`、无 local blockers、production evidence 仍 pending。

## 未改变

- 没有启用真实订单后端 handoff。
- 没有调用真实 DeepSeek/Qwen API。
- 没有改变 signal-only/no-direct-order/backtest gate/user confirmation/hard-risk 边界。
- 没有改变 memory ownership：memory read/add/update/delete/limit 仍要求当前用户上下文。
- 没有合并分支。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮提交后继续只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 完成度仍以 strict-local completion audit 和一键本地 acceptance runner 为准；完整一键命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen profile/API key 和生产审批 evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。
