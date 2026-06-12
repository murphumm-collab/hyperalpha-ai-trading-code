# 2026-06-13 Account LLM connection error safety

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。本轮收紧 Account LLM connection test 的公开错误回显和 redirect 边界，避免用户/模型 endpoint、provider failure body、raw exception、API key/token 或用户输入 model 字符串进入 To C 前端错误提示。

## 已完成

- `backend/api/account_routes.py`
  - 新增固定 public error label：`SAFE_LLM_CONNECTION_TEST_FAILED_MESSAGE`、`SAFE_LLM_CONNECTION_TIMEOUT_MESSAGE`、`SAFE_LLM_INVALID_RESPONSE_MESSAGE`。
  - Account `/api/account/test-llm` 的 ConnectionError、Timeout、RequestException、JSON parse failure、unexpected failure 和 provider non-OK response 不再返回 endpoint、base_url、`str(e)`、provider body 或 `response.text`。
  - 404 fallback 不再回显用户提供的 `model` 字符串，只返回固定 `Model not found or endpoint not available.`。
  - Account route 内全部 `requests.post` 都显式 `allow_redirects=False`，包括 LLM connection test 和 Hyperliquid builder-fee status checks。
  - 日志移除 endpoint/raw response/full message 拼接，避免把 provider/request 异常文本写入普通日志。
- `backend/tests/test_account_llm_connection_error_safety.py`
  - 覆盖 connection endpoint/exception 不回显。
  - 覆盖 RequestException 使用固定 public label。
  - 覆盖 provider failure body 不返回前端。
  - 覆盖 404 不回显 user-supplied model。
  - 覆盖 account route `requests.post` redirect guard。
  - source guard 阻止 `response.text`、`str(e)`、endpoint/base URL 拼回错误消息。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 和 AI Trading regression 纳入 `tests/test_account_llm_connection_error_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - aggregate runner 必须包含 `tests/test_account_llm_connection_error_safety.py`。
  - status 必须包含 `| AI Trading account LLM connection error safety | Done |`，缺失时 local V1 completion audit fail closed。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 account LLM connection error safety Done marker。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 新增本轮 focused evidence 和安全边界说明。

## 验证

- Passed: `cd backend && uv run python -m py_compile api/account_routes.py tests/test_account_llm_connection_error_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- Passed: `cd backend && uv run pytest tests/test_account_llm_connection_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "account_llm_connection_error_safety or current_repo_completion_audit"` returned 9 passing tests.
- Passed: `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
- Passed: `cd backend && uv run pytest tests/test_account_llm_connection_error_safety.py tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q` returned 214 passing tests.
- Passed: `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` returned `local_v1_accepted=true`, `ready_for_live_orders=false`, `github_upload=pushed_to_origin`, `git_governance.status=accepted`, current branch `codex/ai-agent-multitenant-foundation`, and no local blockers.

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
