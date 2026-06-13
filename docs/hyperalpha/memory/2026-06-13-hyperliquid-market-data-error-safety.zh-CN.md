# Hyperliquid Market Data Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 Hyperliquid 行情数据与 K-line collector 的安全错误面。
- 防止 native ticker、HIP-3 candleSnapshot、market-status、K-line selected-symbol fallback 在失败时把 raw provider exception、上游 URL、Bearer/token、private key、API key 或 secret-like 文本写进公开响应或普通日志。
- 本轮不改变 AI Trading signal-only 边界，不打开真实订单后端 handoff，不改变 `ready_for_live_orders=false`。

## 已完成

- `backend/services/hyperliquid_market_data.py`
  - native `metaAndAssetCtxs` ticker request 设置 `allow_redirects=False`。
  - HIP-3 `candleSnapshot` request 设置 `allow_redirects=False`。
  - `get_market_status()` 失败时返回固定公开 label：`Hyperliquid market status is temporarily unavailable`，不再返回 `str(e)`。
  - market preload/init/price/ticker/fallback/K-line/persist/symbol-list/HIP-3 parse/persist 失败日志改为固定 message + `error_type` metadata，不记录 raw exception text。

- `backend/services/kline_collectors.py`
  - `get_supported_symbols()` 从 `hyperliquid_symbol_service` 读取失败时只记录固定 message + `error_type` metadata。
  - fallback 仍保持 `["BTC"]`，不扩大交易或行情范围。

- `backend/tests/test_hyperliquid_market_data_error_safety.py`
  - 覆盖 native ticker request no-redirect 与安全日志。
  - 覆盖 market-status fixed public error，不回显 secret-like 异常。
  - 覆盖 HIP-3 K-line request no-redirect 与安全日志。
  - 覆盖 K-line collector selected-symbol fallback 日志不回显 raw exception。
  - Source guard 扫描 `requests.post` 均要求 `allow_redirects=False`，并防止旧的 raw exception logging/`'error': str(e)` 回归。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `services/hyperliquid_market_data.py`、`tests/test_hyperliquid_market_data_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_market_data_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid market data error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增 current repo source guard，以及缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile services/hyperliquid_market_data.py services/kline_collectors.py tests/test_hyperliquid_market_data_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_market_data_error_safety.py -q`：5 passing tests。
- `cd backend && uv run python -m py_compile services/hyperliquid_market_data.py services/kline_collectors.py tests/test_hyperliquid_market_data_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_market_data_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_market_data_error_safety"`：8 passing tests。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_market_data_error_safety.py tests/test_hyperliquid_symbol_service_error_safety.py tests/test_hyperliquid_read_route_error_safety.py tests/test_hyperliquid_execution_route_error_safety.py tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：285 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`，latest memory accepted，无本地 blockers。
- `git diff --check`：通过。

## 边界

- 本轮没有改变 AI Trading signal-only / disabled-by-default order-backend handoff 边界。
- 行情/K-line 失败仍然 fail closed，公开面只显示固定安全 label 或空 fallback，不显示 raw provider details。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 继续按同一方式检查剩余 exchange/data services 是否存在 raw exception logging 或 redirect-following 外部请求。
- 真实生产验收仍必须另走 production evidence：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
