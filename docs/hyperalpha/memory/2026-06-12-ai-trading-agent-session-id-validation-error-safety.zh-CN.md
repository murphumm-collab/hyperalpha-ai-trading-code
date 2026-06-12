# 2026-06-12 AI Trading Agent Session ID Validation Error Safety Memory

## 本轮新增

- AI Trading `agent_session_id` 的格式校验不再依赖 FastAPI/Pydantic regex/max-length 自动 422：
  - request body、path、query 中的 `agent_session_id` 先进入 service 层 `_clean_agent_session_id()`。
  - 含 credential-like label 的 id 返回固定 400：`agent_session_id must not contain ...`。
  - 超长或格式非法 id 返回固定 400：`agent_session_id must be 1-80 chars ...`。
  - 响应不回显 raw id，例如 `session:api_key=secret-validation-echo` 或超长字符串。
- Completion audit 新增：
  - `| AI Trading agent-session id validation error safety | Done |`

## 已验证

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "agent_session_id_rejects_sensitive_values_without_echo"`

## 边界

- Branch: `codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。
- Local acceptance command: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`
- Default production readiness DB-audit gate remains blocked.
- default production readiness DB-audit blocker: 未提供真实生产 DB audit / 外部 evidence 前保持阻断。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部生产验收。
- 本轮不触发真实交易所请求、真实模型调用、订单后端 handoff 或 live order 解锁。
- 本轮仍保持 `ready_for_live_orders=false`；真实 macOS reboot、真实 Auth/admin 登录态和真实交易所执行仍是外部 pending。
