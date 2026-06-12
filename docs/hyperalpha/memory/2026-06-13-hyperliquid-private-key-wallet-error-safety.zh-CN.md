# Hyperliquid Private-Key Wallet Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续推进 HyperAlpha / Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 本轮只收口普通 Hyperliquid private-key wallet 路由：
  - `GET /api/hyperliquid/accounts/{account_id}/wallet`
  - `POST /api/hyperliquid/accounts/{account_id}/wallet`
  - `DELETE /api/hyperliquid/accounts/{account_id}/wallet`
  - `POST /api/hyperliquid/accounts/{account_id}/wallet/test`
- 暂不把 agent-wallet upgrade/bind 路由并入本切片；那部分需要单独做公开错误、SDK result、审批失败、绑定状态的安全收口。

## 已完成

- `backend/api/hyperliquid_routes.py`
  - 新增固定公开错误 label：
    - `SAFE_HYPERLIQUID_WALLET_CONFIG_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_WALLET_INVALID_PRIVATE_KEY_MESSAGE`
    - `SAFE_HYPERLIQUID_WALLET_DELETE_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_WALLET_TEST_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_WALLET_READ_FAILED_MESSAGE`
  - private-key parse、encryption、storage、delete、balance fetch、connection test unexpected failure 都返回固定 public detail 或 fixed response error。
  - 相关日志改为 metadata-only `error_type`，不记录 raw exception text、private key、API key、Bearer/token、upstream URL。
  - 普通 wallet mainnet builder auth status check 的 `requests.post` 加上 `allow_redirects=False`。
  - builder approve raw SDK `result` 不再 print，公开/日志侧只保留 bounded `status=ok|err`。

- `backend/tests/test_hyperliquid_wallet_error_safety.py`
  - 覆盖 invalid private key、unexpected owner failure、encryption failure、wallet get failure、delete failure、connection ValueError、connection generic failure、source guard。
  - 测试证明 public payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `api/hyperliquid_routes.py` 和 `tests/test_hyperliquid_wallet_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_wallet_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid private-key wallet error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_wallet_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_wallet_error_safety.py -q`：8 passing tests。
- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_wallet_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_wallet_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_wallet_error_safety or current_repo_completion_audit"`：11 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：232 passing tests。
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

- 下一条安全切片优先处理 `upgrade_wallet_to_agent` / `configure_agent_wallet` / agent-wallet status/check 路由，收口 raw `approve_agent` result、agent private-key parse error、builder fee auth exception、agent bind/storage failure 等公开错误面。
