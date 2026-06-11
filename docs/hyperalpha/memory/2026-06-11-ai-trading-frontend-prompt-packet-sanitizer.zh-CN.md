# AI Trading Frontend Prompt-Packet Sanitizer 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Hyper AI AI Trading review prompts 现在把 strategy spec、model-adjust review packet、backtest summary/evidence/preflight、signal preview/detail、handoff result/attempts/reject result 等 JSON packet 送入聊天输入前，统一经过 `sanitizeAiTradingPromptPacket`。
- `sanitizeAiTradingPromptPacket` 会递归清洗敏感 key，并对 prompt/error/message/summary/evidence/gateway/response/rationale/notes 等文本字段里的 secret-like 内容返回 `[redacted_sensitive_text]`；既有 agent-session context prompt sanitizer 改为复用同一递归清洗路径。
- 正常页面展示、后端返回、DB 审计和 order-backend handoff 数据不变；本轮只保护“前端把审计包塞进模型/聊天上下文前”的边界。
- 新增 frontend source guard，防止 strategy/backtest/signal/handoff review prompt 回退到直接 `JSON.stringify(spec/backtest/preflight/evidence/signal/event/attempts, null, 2)`。
- completion audit 新增 `AI Trading frontend prompt-packet sanitizer` Done 标记要求；缺标记时本地 V1 不可验收。第一次聚焦测试在 status 仍未更新时返回 `1 failed, 101 passed`，证明该 gate 生效。

## 验收状态

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q`：102 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：190 passed，15 个既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，保留既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；runtime readiness 第 1 次等待 frontend/backend/mock gateway 冷启动，第 2 次等待 backend，第 3/24 次 `ready=true`；最新 live local mock handoff 证据为 spec `#131`、signal event `#129`、handoff attempt `#127`、`agent_sessions.total=116`、`handoff_attempts.total=127`。
- 后续仍需在本轮 commit 后重新跑 LaunchAgent/runtime mirror 校验。
- 当前本地 V1 仍走 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：按用户要求跳过。
- 当前分支：`codex/ai-agent-multitenant-foundation`。
- Git 边界：不 push、不 merge。
- Production 边界：default production readiness DB-audit blocker 仍然存在；本地 V1 通过不能代表生产实盘可上线。
- 真实外部验收仍缺：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。

## 后续外部条件

- 真实 macOS 重启恢复验收。
- 真实 DeepSeek/Qwen live model-adjust 验收。
- 真实 HTTPS 订单后端 handoff 验收。
- 真实 Auth/JWKS、硬风控生产值和 admin 登录态可视化验收。
- 真实交易所执行验收另开生产实盘验收。
