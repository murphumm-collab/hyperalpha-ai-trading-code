# AI Trading Production URL Host Secret Redaction Memory

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 本轮完成

- Production handoff checker 现在会检查 `AI_TRADING_SIGNAL_GATEWAY_URL` 的 URL host；如果 host/subdomain label 看起来包含 `api-key`、`secret`、`token`、`password`、`private-key`、`authorization`、`bearer` 或 `sk-` / `pk-` token 形态，则 fail closed。
- Aggregate production readiness checker 现在对 Auth/JWKS URL host 和 order-backend gateway URL host 使用同样的 secret-like host 检查。
- 报告输出不再回显这类 host；`checks.*.url.host` 统一返回 `[redacted_sensitive_url_host]`，同时保留 `host_secret_pattern_detected=true` 作为非敏感操作员信号。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 仍是一键本地 V1 验收入口；后续代码变更后必须重跑该入口或记录明确的未复跑状态。
- default production readiness DB-audit blocker 仍必须在本地 V1 验收中保持阻断；本地 mock ready 不能等同于 production live-order ready。
- 新 blocker：
  - `signal_gateway_url_host_secret_pattern_detected`
  - `auth_jwks_url_host_secret_pattern_detected`
- 本轮只增强 no-network production preflight/reporting 边界；不调用模型、不调用订单后端、不连接交易所、不上传 GitHub。

## 验收证据

- `cd backend && uv run python -m py_compile services/ai_trading_production_handoff_service.py services/ai_trading_production_readiness_service.py tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py -q`：15 passed。
- Completion audit 已新增 `| AI Trading production URL host secret redaction | Done |` 本地验收标记要求；缺该标记时 local V1 不应被接受。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "production_url_host_secret_redaction or current_repo_completion_audit"`：2 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、GitHub upload 仍为 deferred。
- `cd backend && uv run pytest tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_v1_completion_audit.py -q`：117 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_handoff_check.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py -q`：171 passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_operator_preflight.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：223 passed，15 个既有 UTC deprecation warnings。
- 完整一键本地 V1 验收：`AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=5 AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=10 scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 成功。覆盖 223 条聚合回归、production URL host secret redaction、frontend build、LaunchAgent runtime sync、runtime mirror freshness、live local mock handoff。runtime readiness 第 1-7 次等待冷启动，第 8/24 次出现可恢复 `Failed to spawn: python`，第 9/24 次 `ready=true`；最新证据为 spec `#147`、signal event `#145`、handoff attempt `#143`、`agent_sessions.total=132`、`handoff_attempts.total=143`、`model_adjustment.ready=false` / `model_profile_not_configured`。

## 仍未完成

- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未做外部验收。
- 真实 macOS 整机重启、真实 admin 登录态 UI、真实订单后端 handoff、真实交易所执行仍属于外部/生产验收。
- 后续代码变更后仍需重跑 aggregate regression、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
