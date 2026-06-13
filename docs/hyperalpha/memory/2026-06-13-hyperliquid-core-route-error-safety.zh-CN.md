# Hyperliquid Core Route Error Safety 记忆

日期：2026-06-13
分支：`codex/ai-agent-multitenant-foundation`

## 本轮目标

- 继续收口 Hyperliquid 核心 legacy 路由的公开错误面，避免 To C UI 在 setup、environment switch、config、balance、positions 失败时看到 raw DB/provider exception、URL、token 或 private key。
- 本轮范围：
  - `POST /api/hyperliquid/accounts/{account_id}/setup`
  - `POST /api/hyperliquid/accounts/{account_id}/switch-environment`
  - `GET /api/hyperliquid/accounts/{account_id}/config`
  - `GET /api/hyperliquid/accounts/{account_id}/balance`
  - `GET /api/hyperliquid/accounts/{account_id}/positions`

## 已完成

- `backend/api/hyperliquid_routes.py`
  - 新增固定公开错误 label：
    - `SAFE_HYPERLIQUID_SETUP_INVALID_REQUEST_MESSAGE`
    - `SAFE_HYPERLIQUID_SETUP_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_SWITCH_INVALID_REQUEST_MESSAGE`
    - `SAFE_HYPERLIQUID_SWITCH_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_CONFIG_NOT_FOUND_MESSAGE`
    - `SAFE_HYPERLIQUID_CONFIG_READ_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_BALANCE_UNAVAILABLE_MESSAGE`
    - `SAFE_HYPERLIQUID_BALANCE_READ_FAILED_MESSAGE`
    - `SAFE_HYPERLIQUID_POSITIONS_UNAVAILABLE_MESSAGE`
    - `SAFE_HYPERLIQUID_POSITIONS_READ_FAILED_MESSAGE`
  - setup/switch/config/balance/positions failure paths 不再返回 `str(e)` 或拼接底层 exception。
  - 相关 unexpected failure 日志改为固定 message + `error_type` metadata，不记录 raw exception text、private key、API key、Bearer/token、upstream URL。

- `backend/tests/test_hyperliquid_core_route_error_safety.py`
  - 覆盖 setup、switch、config、balance、positions 的 ValueError/RuntimeError 失败路径和 source guard。
  - 测试证明 public payload 不含 `api_key`、`Bearer`、`token=`、`private_key`、`secret`、`orders.internal`。

- 验收链条
  - `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已把 `tests/test_hyperliquid_core_route_error_safety.py` 纳入 backend compile / AI Trading backend regression。
  - `backend/scripts/ai_trading_v1_completion_audit.py` 已要求一键本地验收 runner 包含 `tests/test_hyperliquid_core_route_error_safety.py`。
  - completion audit 已要求 status 文档保留 `| AI Trading Hyperliquid core route error safety | Done |`。
  - `backend/tests/test_ai_trading_v1_completion_audit.py` 新增缺 runner gate / 缺 status marker 的 fail-closed 单测。

## 当前验证

- `cd backend && uv run python -m py_compile api/hyperliquid_routes.py tests/test_hyperliquid_core_route_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_core_route_error_safety.py -q`：6 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_core_route_error_safety"`：2 passing tests。
- `cd backend && uv run pytest tests/test_hyperliquid_core_route_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyperliquid_core_route_error_safety or current_repo_completion_audit"`：9 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run pytest tests/test_hyperliquid_core_route_error_safety.py tests/test_hyperliquid_auxiliary_error_safety.py tests/test_hyperliquid_agent_wallet_error_safety.py tests/test_hyperliquid_wallet_error_safety.py tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q`：256 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：56 passing tests。
- `git diff --check`：通过。

## 边界

- 本轮未改 manual-order / enable / disable / connection-test 等后续 execution-adjacent 路径；这些可以作为下一条安全切片继续收口。
- AI Trading 仍保持 signal-only；Agent 不直接下单。
- `ready_for_live_orders=false` 必须保持，直到真实 production evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍是生产验收 blocker。
- `default production readiness DB-audit blocker` 仍必须在本地验收和 completion audit 中被覆盖。
- 完整一键本地验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。

## 后续建议

- 下一条安全切片可以继续处理 manual-order、enable/disable、connection-test、rate-limit、stats 等更靠近执行面的 Hyperliquid legacy route raw `str(e)`，需要保留下单失败/停启交易的状态语义，同时避免 raw exception 和 provider payload 进入前端或日志。
