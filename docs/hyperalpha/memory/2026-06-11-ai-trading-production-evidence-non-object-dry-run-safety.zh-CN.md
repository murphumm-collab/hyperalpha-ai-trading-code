# AI Trading Production Evidence Non-Object Dry-Run Safety 记忆

日期：2026-06-11
分支：`codex/ai-agent-multitenant-foundation`

## 本轮新增

- Admin `/api/ai-trading/admin/production-evidence-validate` 的 `evidence` 输入从只接受 JSON object 放宽为任意 JSON value，但仍只走安全 dry-run/validator 路径；字符串、数组、数字、布尔和 null 不再依赖 FastAPI/Pydantic 422 错误响应。
- `dry_run` 新增 `accepted_input=json_value_for_safe_validation`、`expected_input=json_object` 和 `root_is_object`，同时继续返回 payload bytes、item key counts、not-stored persistence、no model/order/exchange/GitHub calls、live orders locked 和 metadata-only secret policy。
- Completion audit 对非对象 production evidence 增加 `external_evidence_root_must_be_object` blocker；如果非对象输入里出现 bearer token/API key/secret pattern，只返回 `secret_pattern_count` 和 `external_evidence_secret_pattern_detected` blocker，不回显原始 Authorization/header/token 文本。
- Settings Admin Production Evidence Dry-run safety 面板显示 root object 状态和 expected input，source guard 防止未来 UI 绕过安全投影直接渲染原始 evidence。
- Completion audit 新增 `| AI Trading production evidence non-object dry-run safety | Done |` gate，并把本地验收标题推进到 `Local V1 Evidence Non-Object Dry-Run Safety Accepted / Remote Push Skipped`。

## 当前验证状态

- `cd backend && uv run python -m py_compile api/ai_trading_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_production_readiness_api.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_readiness_api.py -q`：102 条通过，保留 15 条既有 UTC deprecation warnings。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：173 条通过，保留 15 条既有 UTC deprecation warnings。
- `cd frontend && npm run build`：通过，剩余为既有 browser-baseline/Browserslist/chunk-size warnings。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=deferred_by_user_request`、`git_governance.status=accepted`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：通过，覆盖 default production readiness DB-audit blocker 按预期阻断、173 条 AI Trading regression、frontend build、runtime mirror 同步、`--require-runtime-mirror-current` 冷启动重试和 live local mock handoff；最新证据为 strategy spec `#121`、signal event `#119`、handoff attempt `#117`、gateway response `mock_accepted`、runtime `mode=http`、`target_kind=local_mock`、`agent_sessions.total=107`、`handoff_attempts.total=117`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。

## 边界

- 本轮不改变生产实盘边界，不触发真实模型调用、真实订单后端 handoff、真实交易所执行、GitHub 上传或 production evidence 持久化。
- GitHub 上传：按用户要求跳过；不 push、不 merge。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实 admin 登录态 UI、真实 production session visual、macOS 整机重启、真实交易所执行仍是外部未验收项。
