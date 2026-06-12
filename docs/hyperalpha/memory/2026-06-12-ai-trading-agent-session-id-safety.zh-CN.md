# 2026-06-12 AI Trading Agent Session ID Safety Memory

## 本轮新增

- AI Trading `agent_session_id` 现在拒绝 credential-like label：
  - backend `_clean_agent_session_id()` 会拒绝包含 `api_key` / `token` / `secret` / `private_key` / `password` / `authorization` / `bearer` 的 id。
  - backend create/save/list/filter/detail/compress 路径会返回固定 400，不回显原始敏感 id。
  - frontend `cleanAiTradingAgentSessionRouteId()` 会在 session detail route/hash 解析阶段丢弃敏感 id，避免拼进 `/api/ai-trading/agent-sessions/...` 请求路径。
- Completion audit 新增：
  - `| AI Trading agent-session id safety | Done |`

## 已验证

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py scripts/ai_trading_v1_completion_audit.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "agent_session_id_rejects_sensitive_values_without_echo or agent_session_manual_context_rejects_sensitive_values"`
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "agent_session_route_id_rejects_sensitive_values_source_guard or model_config_is_nonblocking"`
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "agent_session_id_safety or current_repo_completion_audit"`

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
