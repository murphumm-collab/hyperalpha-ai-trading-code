# Hyperliquid Symbol Service Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 Hyperliquid symbol service 的安全错误面，避免 ranked-symbol fallback 通过成功响应中的 `error` 字段把 raw provider exception、URL、token 或 private key 返回给前端/API 调用方。
- 本轮范围：
  - `backend/services/hyperliquid_symbol_service.py`
  - `GET /api/hyperliquid/symbols/ranked` 的普通 fallback payload
  - Hyperliquid meta / HIP-3 / ranked symbol outbound request redirect behavior
  - symbol refresh / market stream refresh / watchlist update service logs

## 已完成

- `backend/services/hyperliquid_symbol_service.py`
  - 新增固定公开错误 label：
    - `SAFE_HYPERLIQUID_SYMBOL_META_FETCH_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_RANKED_SYMBOLS_ERROR_MESSAGE`
    - `SAFE_HYPERLIQUID_SYMBOL_REFRESH_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_STREAM_SYMBOL_REFRESH_FAILED_MESSAGE`
  - `get_ranked_symbols()` fallback 不再返回 `"error": str(err)`，改为固定安全 label。
  - Hyperliquid meta、HIP-3 meta、ranked metaAndAssetCtxs outbound `requests.post` 都设置 `allow_redirects=False`。
  - fetch/refresh/stream warning logs 改为固定 message + `error_type` metadata，不记录 raw exception text、provider URL、private key、API key、Bearer/token。
  - `update_selected_symbols()` info log 改为 `symbol_count` metadata，不记录 watchlist symbol 列表。

- `backend/tests/test_hyperliquid_symbol_service_error_safety.py`
  - 覆盖 ranked-symbol fallback fixed error、main meta no-redirect、HIP-3 branch no-redirect、source guard。
  - 测试证明 fallback payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `services/hyperliquid_symbol_service.py` 和 `tests/test_hyperliquid_symbol_service_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_symbol_service_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid symbol service error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile services/hyperliquid_symbol_service.py tests/test_hyperliquid_symbol_service_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_symbol_service_error_safety.py -q`：4 passing tests。
- `rg -n '"error"\\s*:\\s*str\\(err\\)|Failed to fetch Hyperliquid meta info: %s|Failed to fetch HIP-3 symbols: %s|Failed to fetch Hyperliquid ranked symbols: %s|Hyperliquid symbol refresh failed: %s|Unable to update market stream symbols: %s|Unable to update market flow collector: %s' backend/services/hyperliquid_symbol_service.py`：无匹配。
- `cd backend && uv run python -m py_compile services/hyperliquid_symbol_service.py tests/test_hyperliquid_symbol_service_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_symbol_service_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_symbol_service_error_safety"`：6 passing tests。
- `cd backend && uv run pytest tests/test_hyperliquid_symbol_service_error_safety.py tests/test_hyperliquid_read_route_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_symbol_service_error_safety or hyperliquid_read_route_error_safety or current_repo_completion_audit"`：14 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_symbol_service_error_safety.py tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：277 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- ranked-symbol fallback 仍会返回 cached available symbols；只是 `error` 字段改为固定安全 label。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 下一条安全切片可以继续检查 Binance symbol service 是否存在对称的 ranked/error/log surface，或者转向 production evidence UX / live acceptance documentation 的外部验收材料打包。
