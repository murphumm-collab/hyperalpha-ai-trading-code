# Hyperliquid Agent-Wallet Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 延续上一轮普通 private-key wallet 错误安全，本轮收口 Hyperliquid agent-wallet 路由：
  - `POST /api/hyperliquid/accounts/{account_id}/wallet/upgrade-to-agent`
  - `POST /api/hyperliquid/accounts/{account_id}/wallet/agent`
  - `GET /api/hyperliquid/accounts/{account_id}/wallet/agent-status`
  - `GET /api/hyperliquid/wallet-upgrade-check`
  - agent-wallet 内部 `extraAgents` 查询 helper。

## 已完成

- `backend/api/hyperliquid_routes.py`
  - 新增 agent-wallet 固定公开错误 label：
    - `SAFE_HYPERLIQUID_AGENT_WALLET_APPROVAL_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_AGENT_WALLET_CONFIG_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_AGENT_WALLET_INVALID_PRIVATE_KEY_MESSAGE`
    - `SAFE_HYPERLIQUID_AGENT_WALLET_STATUS_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_AGENT_WALLET_UPGRADE_CHECK_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_AGENT_WALLET_UPGRADE_FAILED_MESSAGE`
  - `approve_agent` malformed result / SDK `status=err` 不再把 raw SDK result 或 response body 返回前端，只返回固定 approval failed label。
  - agent private key parse failure 返回固定 400 label，不回显 `EthAccount.from_key` raw exception。
  - bind/encrypt/status/upgrade-check unexpected failure 返回固定 label，日志只记录 metadata-only `error_type`。
  - `_get_extra_agents` 和 mainnet agent-wallet builder-fee check 的 `requests.post` 均使用 `allow_redirects=False`。
  - agent-wallet builder fee check 不再 print raw `max_fee` 或 raw exception text。

- `backend/tests/test_hyperliquid_agent_wallet_error_safety.py`
  - 覆盖 approve-agent err result、upgrade unexpected failure、invalid agent key、bind encrypt failure、agent status failure、upgrade-check failure、extraAgents redirect guard 和 source guard。
  - 测试证明 public payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `tests/test_hyperliquid_agent_wallet_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_agent_wallet_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid agent-wallet error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_agent_wallet_error_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_agent_wallet_error_safety.py -q`：8 passing tests。
- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_agent_wallet_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_agent_wallet_error_safety or current_repo_completion_audit"`：11 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：242 passing tests。
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

- 下一条安全切片可以继续收口 `get_trading_mode` / `set_trading_mode` / `wallets/all` 等 Hyperliquid 辅助路由的 raw `str(e)`，或转回前端交互/验收链路。
