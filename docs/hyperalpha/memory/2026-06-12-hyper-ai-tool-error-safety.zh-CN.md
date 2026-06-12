# 2026-06-12 Hyper AI 工具错误输出安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的安全多用户 Agent 底座。
- 本轮聚焦 Hyper AI direct tool / dispatcher：工具执行失败时，不能把底层 raw exception text、provider details、URL、API key/token/secret/private key/password、DB URL 或 exception class name 回传到 Agent 上下文。

## 已完成

- `backend/services/hyper_ai_tools.py`
  - 新增 `_safe_tool_error_payload`、`_safe_tool_item_error`、`_safe_llm_connection_failed_payload` 和安全 tool name 过滤。
  - 多个 `execute_*` 工具的兜底异常从 `{"error": str(e)}` 改为固定安全 envelope：`error`、`error_code`、`tool`。
  - `get_wallet_status` 的单钱包失败不再回显 exchange/client 异常。
  - `web_search` / `fetch_url` 失败不再返回 provider exception 或用户 URL。
  - `create_ai_trader` / `update_ai_trader` 的 LLM 连接失败不再返回 provider/backend `message`。
  - dispatcher 兜底不再返回 `_error_class` 或 raw exception text。
- `backend/tests/test_hyper_ai_tool_error_safety.py`
  - 新增 dispatcher redaction、direct tool redaction、wallet item redaction、source guard 回归。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 与 AI Trading backend regression 纳入 `services/hyper_ai_tools.py` / `tests/test_hyper_ai_tool_error_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - local acceptance runner requirement 纳入 `tests/test_hyper_ai_tool_error_safety.py`。
  - status marker requirement 新增 `AI Trading Hyper AI tool error safety`。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo 与 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Scope bullet、Done marker 和本轮 focused verification evidence。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 新增本轮 focused safety 验收证据。

## 验证

- `cd backend && uv run python -m py_compile services/hyper_ai_tools.py tests/test_hyper_ai_tool_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_tool_error_safety.py -q`：4 passed。
- Static source search：`hyper_ai_tools.py` 无 raw `{"error": str(e)}`、`"error": str(e)`、`_error_class`、provider message、`e.detail`、search error 或 fetch URL error echo path。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_tool_error_safety or current_repo_completion_audit"`：2 passed。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`、current branch `codex/ai-agent-multitenant-foundation`、local blockers 为空。

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
