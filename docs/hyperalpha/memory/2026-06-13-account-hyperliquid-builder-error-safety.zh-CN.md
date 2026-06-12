# 2026-06-13 Account Hyperliquid builder error safety

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。本轮收紧 Account Hyperliquid builder authorization 相关接口的公开错误和上游响应回显，避免 builder fee check / approve / mainnet scan 把 API key、Bearer token、URL、raw exception 或 SDK 原始 result 暴露给 To C 前端。

## 已完成

- `backend/api/account_routes.py`
  - 新增固定 public error label：
    - `SAFE_BUILDER_AUTHORIZATION_CHECK_FAILED_MESSAGE`
    - `SAFE_BUILDER_APPROVAL_FAILED_MESSAGE`
    - `SAFE_BUILDER_MAINNET_CHECK_FAILED_MESSAGE`
    - `SAFE_BUILDER_AUTHORIZATION_FAILED_MESSAGE`
  - `/api/account/hyperliquid/check-builder-authorization` 的 network/general failure 不再返回 `str(e)`。
  - `/api/account/hyperliquid/approve-builder` 的 exception detail 不再返回 `str(e)`。
  - `approve-builder` 失败时不再把 SDK `response` / raw `result` 返回前端，公开响应只保留 bounded `result.status` (`ok` / `err`)。
  - `/api/account/hyperliquid/check-mainnet-accounts` 的 outer failure 不再返回 `str(e)`；per-account scan failure 只记录 account id 和 exception type。
  - builder-auth 日志/print 移除 raw SDK result 和 raw exception text。
- `backend/tests/test_account_hyperliquid_builder_error_safety.py`
  - 覆盖 builder authorization network error 固定 detail。
  - 覆盖 builder authorization JSON/body failure 固定 detail。
  - 覆盖 approve-builder SDK err result 不回显 raw response。
  - 覆盖 approve-builder exception 固定 detail。
  - 覆盖 mainnet-account scan outer failure 固定 detail。
  - source guard 防止 `str(e)` / `result={result}` / raw SDK response 回归。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 和 AI Trading regression 纳入 `tests/test_account_hyperliquid_builder_error_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - aggregate runner 必须包含 `tests/test_account_hyperliquid_builder_error_safety.py`。
  - status 必须包含 `| AI Trading account Hyperliquid builder error safety | Done |`，缺失时 local V1 completion audit fail closed。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 account Hyperliquid builder error safety Done marker。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 新增本轮 focused evidence 和安全边界说明。

## 验证

- Passed: `cd backend && uv run python -m py_compile api/account_routes.py tests/test_account_hyperliquid_builder_error_safety.py`
- Passed: `cd backend && uv run pytest tests/test_account_hyperliquid_builder_error_safety.py -q` returned 6 passing tests.
- Passed: `cd backend && uv run python -m py_compile api/account_routes.py tests/test_account_hyperliquid_builder_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- Passed: `cd backend && uv run pytest tests/test_account_hyperliquid_builder_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "account_hyperliquid_builder_error_safety or current_repo_completion_audit"` returned 9 passing tests.
- Passed: `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
- Passed: `cd backend && uv run pytest tests/test_account_hyperliquid_builder_error_safety.py tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q` returned 222 passing tests.
- Passed: `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` returned `local_v1_accepted=true`, `ready_for_live_orders=false`, `github_upload=pushed_to_origin`, `git_governance.status=accepted`, current branch `codex/ai-agent-multitenant-foundation`, and no local blockers.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 56 passing tests.
- Passed: `git diff --check`.

## 仍不改变

- `ready_for_live_orders` 必须继续保持 `false`。
- 真实 DeepSeek/Qwen API key live model-adjust 仍未验收。
- 真实 HyperAlpha 订单后端 URL/token live handoff 仍未验收。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍属于外部验收。
- Full local acceptance command remains `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`; default production readiness DB-audit blocker 继续作为非实盘 gate。

## 分支边界

- 当前分支：`codex/ai-agent-multitenant-foundation`
- 远程目标：`origin/codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation
- 已 push，不 merge
- 不合并，不直接切到生产实盘。
