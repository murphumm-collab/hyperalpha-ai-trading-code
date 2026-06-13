# Market Universe Provider Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 To C AI Trading 标的物列表的 provider 错误面。
- 防止 `/api/ai-trading/market-universe` 在 Hyperliquid crypto 或 HIP-3 metadata 部分失败时，把 raw upstream exception、secret-like URL、Bearer token、private key 或 provider 内部文本放进 `errors` 返回给前端。
- 防止 market-universe 的 Hyperliquid metadata HTTP 请求跟随重定向。
- 本轮不改变 AI Trading signal-only 边界，不打开真实订单后端 handoff，不改变 `ready_for_live_orders=false`。

## 已完成

- `backend/services/ai_trading_market_universe_service.py`
  - `_fetch_meta_and_asset_contexts()` 的 `requests.post(...)` 已显式设置 `allow_redirects=False`。
  - 新增 `SAFE_MARKET_UNIVERSE_PROVIDER_ERRORS` 固定公开错误 label。
  - crypto provider 失败时，`errors.crypto` 只返回 `hyperliquid_crypto_market_universe_unavailable`。
  - HIP-3 provider 失败时，`errors.hip3` 只返回 `hyperliquid_hip3_market_universe_unavailable`。
  - HIP-3 fallback 仍可从 available-symbol cache 返回安全标的物，不扩大下单能力。

- `backend/tests/test_ai_trading_market_universe_error_safety.py`
  - 覆盖 crypto metadata provider 失败、HIP-3 provider 成功的部分失败路径。
  - 覆盖 HIP-3 metadata provider 失败、available-symbol cache fallback 的路径。
  - 覆盖所有 market-universe `requests.post(...)` 调用必须有 `allow_redirects=False`。
  - Source guard 防止 `errors["crypto"] = str(exc)` / `errors["hip3"] = str(exc)` 回归。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `services/ai_trading_market_universe_service.py` 和 `tests/test_ai_trading_market_universe_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_ai_trading_market_universe_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading market-universe provider error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增 current repo source guard，以及缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile services/ai_trading_market_universe_service.py tests/test_ai_trading_market_universe_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_market_universe_error_safety.py -q`：3 passing tests。
- `cd backend && uv run python -m py_compile services/ai_trading_market_universe_service.py tests/test_ai_trading_market_universe_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_market_universe_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "market_universe_provider_error_safety or market_universe_error_safety"`：7 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_market_universe_error_safety.py tests/test_auth_jwks_error_safety.py tests/test_hyperliquid_market_data_error_safety.py tests/test_hyperliquid_symbol_service_error_safety.py tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：297 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`，latest memory accepted，7 个外部验收项仍按设计 pending。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- market-universe provider 失败仍然 fail closed / degrade safely，公开面只显示固定 source-level label。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 继续检查非 AI Trading legacy routes 是否仍存在 raw exception 公开回显；这些不应阻断本地 V1，但进入 To C production 前需要逐步收口。
- 真实生产验收仍必须另走 production evidence：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
