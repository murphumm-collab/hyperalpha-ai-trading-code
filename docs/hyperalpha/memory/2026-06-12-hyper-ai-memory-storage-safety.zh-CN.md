# 2026-06-12 Hyper AI memory storage 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 上一轮已收紧 Hyper AI memory extraction/dedup prompt 与模型输出写入边界。
- 本轮补齐长期记忆的手工写入、工具写入、历史脏数据读取和 system prompt 注入边界，避免 API key、token、Bearer、authorization、private key、password、DB URL 等 secret-like 文本进入长期记忆或被后续 DeepSeek/Qwen 上下文复用。

## 已完成

- `backend/services/hyper_ai_memory_service.py`
  - 新增 `REDACTED_SENSITIVE_MEMORY_CONTENT`、`SENSITIVE_MEMORY_CONTENT_ERROR`、`is_memory_content_sensitive`、`validate_memory_content_for_storage`。
  - `add_memory` 在写入前验证 content，secret-like content 会 fail closed。
  - `update_memory` 在更新 content 前验证，secret-like content 不会覆盖既有安全记忆。
  - `get_memories` 对 legacy/polluted memory rows 做响应层脱敏，返回 `[redacted_sensitive_memory_content]` 和 `content_redacted=true`，DB 原始审计 row 不被自动改写。
  - `_build_memory_context` 通过 `get_memories` 取得脱敏内容，因此 long-term memory system prompt injection 不会带出 legacy secret。
- `backend/services/hyper_ai_tools.py`
  - `save_memory` 工具在进入 dedup/add 之前检查 content；secret-like content 返回固定 `blocked` 响应，不回显原文。
- `backend/tests/test_hyper_ai_memory_error_safety.py`
  - 新增 manual add/update sensitive content rejection regression。
  - 新增 legacy polluted memory read/system-prompt redaction regression。
  - 新增 `save_memory` tool blocked response regression。
  - source guard 防止 raw `m.content` response 和 raw `memory.content = content` update 回归。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - completion audit 新增 `AI Trading Hyper AI memory storage safety` required marker。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 和 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker，并把 focused memory safety 验证更新为 10 passing tests。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 focused memory error/prompt/storage safety 证据。

## 验证

- `cd backend && uv run python -m py_compile services/hyper_ai_memory_service.py services/hyper_ai_tools.py services/hyper_ai_service.py tests/test_hyper_ai_memory_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_memory_error_safety.py -q`：10 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_memory_error_safety or hyper_ai_memory_prompt_safety or hyper_ai_memory_storage_safety or current_repo_completion_audit"`：14 passed, 155 deselected。
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
