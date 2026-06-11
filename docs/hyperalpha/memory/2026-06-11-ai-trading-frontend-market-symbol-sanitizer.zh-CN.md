# AI Trading Frontend Market Symbol Sanitizer 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- AI Trading market-universe 后端现在过滤 malformed、过长、secret-like 的 symbol/name，不把这类标的物序列化到 market-universe payload。
- Hyper AI AI Trading market selector 现在对 watchlist、AI Trading market-universe、available-symbols 三个来源的 symbol 做前端安全过滤。
- 合法 HIP-3 `dex:symbol` 形态会保留并规范化；不安全 symbol 不会进入 UI 按钮、chat prompt 或 strategy-spec draft 请求。
- `handleTradingSymbolPrompt` 和 `handleStrategySpecDraft` 使用 `safeSymbol` 生成模型提示和 draft body，防止未来后端/缓存回归把 secret-like symbol 插入模型上下文。
- 新增 frontend source guard 和 backend route regression；completion audit 新增 `AI Trading frontend market symbol sanitizer` Done 标记要求，缺标记时本地 V1 不可验收。

## 验收状态

- `cd backend && uv run python -m py_compile services/ai_trading_market_universe_service.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_routes.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_routes.py -q`：149 条通过。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：196 条通过，保留 15 条既有 UTC deprecation warning。
- `cd frontend && npm run build`：通过；仅保留既有 browser-baseline、Browserslist、dynamic-import/chunk-size warning。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过；runtime readiness 第 1 次等待 frontend/backend/mock gateway 冷启动，第 2 次等待 backend，第 3/24 次返回 ready；最新本地 mock 证据为 spec `#134`、signal event `#132`、handoff attempt `#130`、`agent_sessions.total=119`、`handoff_attempts.total=130`。
- 后续仍需在 commit 后重新跑：`scripts/local-dev/install_launch_agent.sh` 和带 `--require-runtime-mirror-current` 的 runtime mirror 校验。
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
