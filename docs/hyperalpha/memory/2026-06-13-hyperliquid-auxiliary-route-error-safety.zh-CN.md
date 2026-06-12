# Hyperliquid Auxiliary Route Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 Hyperliquid 辅助路由的公开错误面，避免 To C UI 在交易模式读取/切换或钱包列表失败时看到 raw DB/provider exception、URL、token 或 private key。
- 本轮范围：
  - `GET /api/hyperliquid/trading-mode`
  - `POST /api/hyperliquid/trading-mode`
  - `GET /api/hyperliquid/wallets/all`

## 已完成

- `backend/api/hyperliquid_routes.py`
  - 新增固定公开错误 label：
    - `SAFE_HYPERLIQUID_TRADING_MODE_READ_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_TRADING_MODE_UPDATE_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_WALLET_LIST_FAILED_MESSAGE`
  - trading-mode get/set 和 wallets/all failure paths 不再返回 `str(e)`。
  - 相关日志改为 metadata-only `error_type`，不记录 raw exception text、private key、API key、Bearer/token、upstream URL。

- `backend/tests/test_hyperliquid_auxiliary_error_safety.py`
  - 覆盖 trading-mode read failure、trading-mode update failure、all-wallet list failure 和 source guard。
  - 测试证明 public payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `tests/test_hyperliquid_auxiliary_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_auxiliary_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid auxiliary route error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_auxiliary_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_auxiliary_error_safety.py -q`：4 passing tests。
- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_auxiliary_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_auxiliary_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_auxiliary_error_safety or current_repo_completion_audit"`：7 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：248 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。
- `git diff --check`：通过。

## 边界

- AI Trading 仍保持 signal-only；Agent 不直接下单。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 下一条安全切片可以继续处理 `setup/switch/balance/positions/manual-order` 等更靠近交易执行的 Hyperliquid legacy route raw `str(e)`，需要更谨慎地保留 400/404/交易失败状态语义。
