# 2026-06-13 Shared AI LLM Redirect Guard

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。上一轮已让 Hyper AI / AI Trading model-adjust / signal gateway 禁止 HTTP redirect following；本轮把同一边界扩展到共享 AI/策略模型服务，避免通过用户配置模型 endpoint 或中间代理 30x 把后端请求带到另一个 URL。

## 已完成

- 以下共享 AI/策略服务的 `requests.post` 已设置 `allow_redirects=False`：
  - `ai_decision_service`
  - `ai_signal_generation_service`
  - `ai_prompt_generation_service`
  - `ai_attribution_service`
  - `ai_program_service`
  - `prompt_backtest_service`
  - `kline_ai_analysis_service`
- 新增 `tests/test_shared_ai_llm_redirect_guard.py`，用 AST source guard 扫描上述模块内所有 `requests.post` 调用，任何缺少 `allow_redirects=False` 的调用都会失败。
- 一键本地验收 runner 已加入 `tests/test_shared_ai_llm_redirect_guard.py` 的 compile 和 pytest 列表。
- Completion audit 新增 `| AI Trading shared AI LLM redirect guard | Done |` 状态 marker，缺测试文件或缺 marker 时本地完成度验收 fail closed。

## 验证

- Passed: `cd backend && uv run python -m py_compile services/ai_attribution_service.py services/ai_signal_generation_service.py services/ai_prompt_generation_service.py services/prompt_backtest_service.py services/kline_ai_analysis_service.py services/ai_decision_service.py services/ai_program_service.py tests/test_shared_ai_llm_redirect_guard.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- Passed: `cd backend && uv run pytest tests/test_shared_ai_llm_redirect_guard.py -q` returned 1 passing test.
- Passed: `cd backend && uv run pytest tests/test_shared_ai_llm_redirect_guard.py tests/test_ai_trading_v1_completion_audit.py -q -k "shared_ai_llm_redirect_guard or current_repo_completion_audit"` returned 4 passing tests.
- Passed: `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
- Passed: `cd backend && uv run pytest tests/test_shared_ai_llm_redirect_guard.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q` returned 203 passing tests.
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
