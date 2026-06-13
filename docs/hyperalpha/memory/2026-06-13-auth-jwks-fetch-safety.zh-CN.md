# Auth JWKS Fetch Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口生产 Auth/JWKS 相关的公开错误面。
- 防止 verified-bearer JWKS 拉取失败时把 raw provider exception、secret-like JWKS URL、Bearer token、private key 或其他敏感文本暴露给前端/API 调用方。
- 防止 JWKS HTTP 拉取跟随重定向，把 auth provider 请求带到非预期目标。
- 本轮不改变 AI Trading signal-only 边界，不打开真实订单后端 handoff，不改变 `ready_for_live_orders=false`。

## 已完成

- `backend/api/auth_utils.py`
  - `_get_jwks_keys()` 的 `requests.get(jwks_url, timeout=10)` 改为 `requests.get(jwks_url, timeout=10, allow_redirects=False)`。
  - JWKS 拉取异常仍固定返回 `HTTPException(status_code=503, detail="Unable to fetch JWKS")`，不回显 provider exception。
  - 成功拉取的 JWKS keys 继续按 `AUTH_JWKS_CACHE_SECONDS` 缓存，避免扩大网络调用面。

- `backend/tests/test_auth_jwks_error_safety.py`
  - 覆盖 JWKS fetch 失败时返回固定公开错误，不泄露 bearer token、secret-like JWKS URL、private key 或 raw exception。
  - 覆盖 JWKS fetch 成功时使用 `allow_redirects=False`，并确认第二次读取命中 cache。
  - Source guard 扫描 `auth_utils.py` 中所有 `requests.get(...)` 调用，要求显式 `allow_redirects=False`，防止旧写法回归。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `api/auth_utils.py` 和 `tests/test_auth_jwks_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_auth_jwks_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Auth JWKS fetch safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增 current repo source guard，以及缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/auth_utils.py tests/test_auth_jwks_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_auth_jwks_error_safety.py -q`：3 passing tests。
- `cd backend && uv run python -m py_compile api/auth_utils.py tests/test_auth_jwks_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_auth_jwks_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "jwks"`：6 passing tests。
- `cd backend && uv run pytest tests/test_auth_jwks_error_safety.py tests/test_hyperliquid_market_data_error_safety.py tests/test_hyperliquid_symbol_service_error_safety.py tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：291 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`，latest memory accepted，7 个外部验收项仍按设计 pending。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- JWKS provider 失败仍然 fail closed，公开面只显示固定安全 label。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 继续检查剩余 auth/provider/network 调用是否存在 redirect-following、raw exception echo 或 secret-bearing URL 回显。
- 真实生产验收仍必须另走 production evidence：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
