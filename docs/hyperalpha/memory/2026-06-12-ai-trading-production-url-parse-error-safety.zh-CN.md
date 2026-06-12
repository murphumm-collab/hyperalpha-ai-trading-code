# AI Trading Production URL Parse-Error Safety Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- Production handoff checker 的 URL helper 现在对 `parsed.hostname` 读取也 fail closed；即使 Python URL parser 或 hostname 属性在 malformed URL 上抛 `ValueError`，production report 也不会中断。
- Aggregate production readiness checker 继续复用同一安全 URL 解析边界，覆盖 Auth/JWKS URL 和 order-backend gateway URL。
- 一键本地验收继续覆盖 default production readiness DB-audit blocker；本地 mock ready 不能等同于 production live-order ready。
- 报告中对 malformed URL parse error 返回 `parse_error=true`、`host=null`、`port=null`，并保持 `credentials_embedded=false` / `query_present=false` 等非敏感默认值。
- 新增/锁定 blocker：
  - `signal_gateway_url_invalid`
  - `auth_jwks_url_invalid`
- Completion audit 现在要求 status 文档存在 `| AI Trading production URL parse-error safety | Done |`；缺该标记时 local V1 acceptance 会 fail closed。
- 本轮只增强 no-network production preflight/readiness reporting；不调用模型、不调用订单后端、不连接交易所、不上传 GitHub。

## 验收证据

- `cd backend && uv run python -m py_compile services/ai_trading_production_handoff_service.py services/ai_trading_production_readiness_service.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py -q`：19 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "production_url_parse_error_safety or production_url_port_safety or current_repo_completion_audit"`：3 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub upload 仍为 deferred。
- `cd backend && uv run pytest tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_v1_completion_audit.py -q`：123 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py -q`：177 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：229 passed，15 个既有 UTC deprecation warnings。
- 完整一键本地 V1 验收：第一次在 DB-audit gate 命中 macOS 临时 `fork: Resource temporarily unavailable`；等待后重跑 `AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 成功。覆盖 229 条聚合回归、production URL host secret redaction、production URL port safety、production URL parse-error safety、frontend build、LaunchAgent runtime sync、runtime mirror freshness、live local mock handoff。runtime readiness 第 1-2 次等待 frontend/backend/mock gateway 冷启动，第 3 次等待 frontend/backend，第 4-7 次等待 backend，第 8/24 次 `ready=true`。
- 最新 local/mock evidence：spec `#149`、signal event `#147`、handoff attempt `#145`、gateway response `mock_accepted`、runtime `mode=http`、runtime `target_kind=local_mock`、`agent_sessions.total=135`、`handoff_attempts.total=145`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 后续代码变更后仍需重跑 aggregate regression、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
