# Hyperliquid Read Route Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 Hyperliquid read/admin-adjacent legacy 路由的公开错误面，避免 To C UI 在 snapshots、symbols、watchlist 或 action summary 失败时看到 raw DB/provider exception、URL、token 或 private key。
- 本轮范围：
  - `GET /api/hyperliquid/accounts/{account_id}/snapshots`
  - `GET /api/hyperliquid/symbols/available`
  - `GET /api/hyperliquid/symbols/ranked`
  - `GET /api/hyperliquid/symbols/watchlist`
  - `PUT /api/hyperliquid/symbols/watchlist`
  - `GET /api/hyperliquid/actions/summary`

## 已完成

- `backend/api/hyperliquid_routes.py`
  - 新增固定公开错误 label：
    - `SAFE_HYPERLIQUID_SNAPSHOT_READ_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_SYMBOL_LIST_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_SYMBOL_RANKING_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_WATCHLIST_READ_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_WATCHLIST_UPDATE_INVALID_REQUEST_MESSAGE`
    - `SAFE_HYPERLIQUID_WATCHLIST_UPDATE_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_ACTION_SUMMARY_READ_FAILED_MESSAGE`
  - snapshots / symbols / watchlist read/update / action summary failure paths 不再返回 `str(e)` 或拼接底层 exception。
  - watchlist update 的 info log 改成 metadata-only `symbol_count`，不记录用户提交的 symbol 列表。
  - 相关 unexpected failure 日志改为固定 message + `error_type` metadata，不记录 raw exception text、private key、API key、Bearer/token、upstream URL。

- `backend/tests/test_hyperliquid_read_route_error_safety.py`
  - 覆盖 snapshots DB failure、available/ranked symbols failure、watchlist read/update ValueError/RuntimeError、action summary failure 和 source guard。
  - 测试证明 public payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `tests/test_hyperliquid_read_route_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_read_route_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid read route error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_read_route_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_read_route_error_safety.py -q`：5 passing tests。
- `rg -n 'detail=str\\(|str\\(err\\)|str\\(e\\)|logger\\.error\\(f\\\".*\\{(err|e)\\}|exc_info=True' backend/api/hyperliquid_routes.py`：无匹配。
- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_read_route_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_read_route_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_read_route_error_safety"`：7 passing tests。
- `cd backend && uv run pytest tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_read_route_error_safety or hyperliquid_execution_route_error_safety or hyperliquid_core_route_error_safety or current_repo_completion_audit"`：24 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：271 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- 这些路由仍是 read/admin-adjacent support surfaces，本轮只处理错误公开面和日志泄露面。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 下一条安全切片可以继续处理 Hyperliquid route 的 remaining explicit public messages 是否需要统一成 safe constants，或者转向 production evidence UX / live acceptance documentation 的外部验收材料打包。
