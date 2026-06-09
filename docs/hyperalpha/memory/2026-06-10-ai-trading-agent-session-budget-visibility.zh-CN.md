# 2026-06-10 AI Trading Agent Session Budget Visibility Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading agent session 自身、嵌套 audit payload、context packet 和前端 UI 都可以看到上下文摘要长度和最大字符预算。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- Backend：
  - 新增 `_agent_context_summary_budget_fields`，统一返回：
    - `context_summary_chars`
    - `summary_max_chars`
  - `serialize_ai_trading_agent_session_record` 现在返回 session 摘要长度和 `summary_max_chars=2000`。
  - strategy spec / signal event / handoff attempt 的嵌套 `agent_session` payload 也返回同样字段。
  - 嵌套 payload 在有 `db/user_id` 时会从当前用户 agent session 主记录回填 name/status/context summary，避免 signal event / attempt 因自身不复制 summary 而显示 `0`。
  - agent-session list 和 `/agent-sessions/{id}/context` 的 `agent_session` 也返回 budget 字段。
  - context compression 写回 summary 后同步刷新 `context_summary_chars`。

- Frontend：
  - `AiTradingAgentSessionRecord`、context packet、strategy/signal/attempt nested session 类型补充 budget 字段。
  - AI Trading 右侧 session summary 输入上方显示 `Context n / 2000`，新会话编辑时按当前草稿长度实时显示。
  - Recent/Archived agent sessions 显示紧凑 `ctx n / 2000`。
  - Agent-session detail 页的 context limits 区块显示 `Summary chars n / 2000`，同时保留 `redacted, no credentials`。

- 测试：
  - Route regression 覆盖 active session list、filtered specs、filtered signal events、handoff attempts、context packet、session CRUD、update、compress 后的 `context_summary_chars` 和 `summary_max_chars=2000`。
  - 覆盖 signal event / handoff attempt 通过 current-user session 主记录回填 context budget。
  - CRUD 测试使用非敏感 summary；敏感 summary 脱敏仍由既有 `[redacted_sensitive_context]` 测试覆盖。

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py api/ai_trading_routes.py tests/test_ai_trading_routes.py`
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：35 passed。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：59 passed，4 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：passed，剩余为既有 browser baseline / Browserslist / chunk-size warnings。
- `scripts/local-dev/install_launch_agent.sh`：passed。
- 首次 strict env check 命中 backend 冷启动；确认 8802 已监听后重试 `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict`：`ready=true`，runtime totals 为 strategy specs `35`、signal events `33`、agent sessions `20`、handoff attempts `31`。
- In-app Browser：
  - `/app/ai-trading` 跳过本地 onboarding 后显示 `Agent session`、`Context 0 / 2000`，Recent agent sessions 显示 `ctx 0 / 2000`。
  - `/app/ai-trading/sessions/ait%3Abtc%3A4d53a40f6789` 跳过本地 onboarding 后显示 `Agent session detail`、`Context limits`、`Summary chars 0 / 2000`、`redacted, no credentials`、Session specs/signals/handoff attempts。
  - 未输入 API key，未触发 handoff 或订单动作。

## 下一步注意

- 这只是可见性和审计字段，不触发真实模型调用或真实订单发送。
- AI 仍是 signal-only；真实订单执行仍必须由订单后端处理。
- 真实 DeepSeek/Qwen profile/API key、真实订单后端 URL/token、真实 Auth/JWKS、真实登录态 admin/user 可视化验收仍未接受。
