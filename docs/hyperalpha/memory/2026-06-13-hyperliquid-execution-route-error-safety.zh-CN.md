# Hyperliquid Execution Route Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 Hyperliquid execution-adjacent legacy 路由的公开错误面，避免 To C UI 在手动下单、启停交易、连接测试、rate-limit 或 trading-stats 失败时看到 raw DB/provider exception、URL、token 或 private key。
- 本轮范围：
  - `POST /api/hyperliquid/accounts/{account_id}/orders/manual`
  - `POST /api/hyperliquid/accounts/{account_id}/disable`
  - `POST /api/hyperliquid/accounts/{account_id}/enable`
  - `GET /api/hyperliquid/accounts/{account_id}/test-connection`
  - `GET /api/hyperliquid/accounts/{account_id}/rate-limit`
  - `GET /api/hyperliquid/accounts/{account_id}/trading-stats`

## 已完成

- `backend/api/hyperliquid_routes.py`
  - 新增固定公开错误 label：
    - `SAFE_HYPERLIQUID_ORDER_INVALID_REQUEST_MESSAGE`
    - `SAFE_HYPERLIQUID_ORDER_PLACEMENT_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_DISABLE_INVALID_REQUEST_MESSAGE`
    - `SAFE_HYPERLIQUID_DISABLE_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_ENABLE_INVALID_REQUEST_MESSAGE`
    - `SAFE_HYPERLIQUID_ENABLE_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_CONNECTION_TEST_UNAVAILABLE_MESSAGE`
    - `SAFE_HYPERLIQUID_CONNECTION_TEST_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_RATE_LIMIT_READ_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_TRADING_STATS_READ_FAILED_MESSAGE`
  - manual-order / enable / disable / connection-test / rate-limit / trading-stats failure paths 不再返回 `str(e)` 或拼接底层 exception。
  - manual-order、enable、disable、connection-test 现在显式 pass-through `HTTPException`，避免 account 404 或 leverage 400 被 generic handler 改成 500。
  - connection-test 保留原有 200 failure payload 形态，但 `error` 字段改成固定公开 label。
  - 相关 unexpected failure 日志改为固定 message + `error_type` metadata，不记录 raw exception text、private key、API key、Bearer/token、upstream URL。

- `backend/tests/test_hyperliquid_execution_route_error_safety.py`
  - 覆盖 manual-order HTTPException pass-through、manual-order ValueError/RuntimeError、enable/disable ValueError/RuntimeError、connection-test ValueError/RuntimeError response、rate-limit/trading-stats RuntimeError 和 source guard。
  - 测试证明 public payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `tests/test_hyperliquid_execution_route_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_execution_route_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid execution route error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_execution_route_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_execution_route_error_safety.py -q`：6 passing tests。
- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_execution_route_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_execution_route_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_execution_route_error_safety"`：8 passing tests。
- `cd backend && uv run pytest tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_execution_route_error_safety or hyperliquid_core_route_error_safety or current_repo_completion_audit"`：17 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：264 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- manual-order 仍是 legacy direct endpoint，本轮只处理错误公开面和 HTTPException status pass-through，不新增任何自动实盘路径。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 下一条安全切片可以继续处理 Hyperliquid watchlist/action-summary/snapshot/symbol discovery 等 read/admin-adjacent legacy route logging，或者转向 AI Trading production evidence UX 的外部验收材料打包。
