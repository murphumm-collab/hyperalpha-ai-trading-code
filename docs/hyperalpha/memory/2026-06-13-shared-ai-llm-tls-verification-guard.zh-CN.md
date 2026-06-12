# 2026-06-13 Shared AI LLM TLS Verification Guard

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。上一轮已禁止模型 HTTP redirect following；本轮收紧模型传输层 TLS 校验，避免用户/平台 LLM endpoint 在生产路径中硬编码跳过证书验证。

## 已完成

- 新增 `services/llm_transport_security.py`：
  - 默认 `llm_tls_verify_enabled()` 返回 `True`
  - 只有显式 `HYPER_AI_ALLOW_INSECURE_LLM_TLS=true` 时才返回 `False`
- 以下模型请求不再硬编码 `verify=False`，改为默认验证 TLS：
  - Account LLM connection test
  - `ai_decision_service`
  - `prompt_backtest_service`
  - `kline_ai_analysis_service`
  - `news_ai_classifier`
- `tests/test_shared_ai_llm_redirect_guard.py` 新增 TLS source guard：扫描相关模块，任何 literal `verify=False` 都会失败。
- 一键本地验收 runner 已把 `services/llm_transport_security.py` 加入 compile 清单。
- Completion audit 新增 `| AI Trading shared AI LLM TLS verification guard | Done |` 状态 marker，缺 marker 时本地完成度验收 fail closed。

## 验证

- Passed: `cd backend && uv run python -m py_compile services/llm_transport_security.py services/ai_decision_service.py api/account_routes.py services/prompt_backtest_service.py services/kline_ai_analysis_service.py services/news_ai_classifier.py tests/test_shared_ai_llm_redirect_guard.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- Passed: `cd backend && uv run pytest tests/test_shared_ai_llm_redirect_guard.py -q` returned 3 passing tests.
- Passed: `rg -n "verify\\s*=\\s*False|verify=False" backend/services backend/api backend/tests backend/scripts scripts/local-dev -g '!**/__pycache__/**'` returned no matches.
- Passed: `cd backend && uv run pytest tests/test_shared_ai_llm_redirect_guard.py tests/test_ai_trading_v1_completion_audit.py -q -k "shared_ai_llm_tls_verification_guard or shared_ai_llm_redirect_guard or current_repo_completion_audit"` returned 7 passing tests.
- Passed: `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
- Passed: `cd backend && uv run pytest tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q` returned 206 passing tests.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 56 passing tests.
- Passed: `git diff --check`
- Passed: `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` returned `local_v1_accepted=true`, `ready_for_live_orders=false`, `github_upload=pushed_to_origin`, `git_governance.status=accepted`, accepted latest memory pointer, and no local blockers.

## 仍不改变

- 真实 DeepSeek/Qwen API key live model-adjust 仍未验收。
- 真实 HyperAlpha 订单后端 URL/token handoff 仍未验收。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍属于外部验收。
- Full local acceptance command remains `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`; default production readiness DB-audit blocker 继续作为非实盘 gate。
- `ready_for_live_orders` 必须继续保持 `false`。

## 分支边界

- 当前分支：`codex/ai-agent-multitenant-foundation`
- 远程目标：`origin/codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation
- 已 push，不 merge
- 不合并，不直接切到生产实盘。
