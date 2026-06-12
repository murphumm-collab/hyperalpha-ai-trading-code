# 2026-06-12 AI Trading route exception detail 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的安全多用户 Agent 底座。
- 上一轮已完成 Hyper AI service stream 错误输出脱敏；本轮收口 AI Trading API route 层的异常 detail，避免未来 service/依赖异常把 URL、API key、token、authorization、Bearer、private key 或 secret-like 文本直接回显给前端。

## 已完成

- `backend/api/ai_trading_routes.py`
  - 新增 `SAFE_AI_TRADING_ROUTE_ERROR_DETAIL` 与 `_safe_ai_trading_route_error_detail`。
  - 新增 `_ai_trading_route_value_error` / `_ai_trading_route_exception`，集中处理 route-level `ValueError` 与 `SignalGatewayDisabledError`。
  - 现有 AI Trading route catch 块改为通过统一 helper 返回 HTTPException。
  - 保留原有 400/404/409 状态语义：`not found` 仍映射 404，gateway disabled 仍映射 409。
  - 安全固定文案如 “must not contain API keys/tokens” 不会被误伤；只有带值形态如 `api_key=...`、`Authorization:`、`Bearer <value>` 或 URL 会触发固定安全 detail。
- `backend/tests/test_ai_trading_routes.py`
  - 新增 route exception detail redaction regression，覆盖 400、404、409 三种状态。
  - 新增 source guard，防止重新引入 direct `detail=str(exc)` / `detail=detail`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - status marker requirement 新增 `AI Trading route exception detail safety`。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo 与 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Scope bullet、Done marker 和 focused verification evidence。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 新增本轮 focused safety 验收证据。

## 验证

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py tests/test_ai_trading_routes.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "route_exception_detail or agent_session_id_rejects_sensitive_values_without_echo or manual_context_rejects_sensitive_values or strategy_text_source_safety"`：4 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passed。
- `cd backend && uv run python -m py_compile api/ai_trading_routes.py tests/test_ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py -q -k "route_exception_detail or agent_session_id_rejects_sensitive_values_without_echo or route_exception_detail_safety or current_repo_completion_audit"`：5 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、当前分支 `codex/ai-agent-multitenant-foundation`、无 local blockers。

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
