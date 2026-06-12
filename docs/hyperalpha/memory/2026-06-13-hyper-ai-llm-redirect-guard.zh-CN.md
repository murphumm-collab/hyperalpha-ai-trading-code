# 2026-06-13 Hyper AI LLM Redirect Guard

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。本轮目标是补齐 endpoint 校验后的 HTTP 请求执行层：即使 provider/custom LLM endpoint 或 signal gateway 返回 30x redirect，后端也不能跟随跳转到另一个 URL、内网地址或非预期服务。

## 已完成

- Hyper AI LLM connection test、chat、onboarding stream、insight stream、suggestions 的 outbound `requests.post` 已全部设置 `allow_redirects=False`。
- Hyper AI memory extraction/dedup 和共享 context compression summary 的用户配置 LLM 请求已全部设置 `allow_redirects=False`。
- AI Trading DeepSeek/Qwen model-adjust 请求已设置 `allow_redirects=False`。
- Signal gateway handoff 请求也设置 `allow_redirects=False`，保持订单后端 URL 不被 30x 牵引；这不改变默认禁用 handoff、不打开实盘。
- 新增 AST source guard：扫描 `hyper_ai_service`、`hyper_ai_memory_service`、`ai_context_compression_service`、`ai_trading_strategy_spec_service` 中所有 `requests.post`，任何调用缺少 `allow_redirects=False` 都会失败。
- Completion audit 新增 `| AI Trading Hyper AI LLM redirect guard | Done |` 状态 marker，缺 marker 时本地完成度验收 fail closed。

## 验证

- Passed: `cd backend && uv run python -m py_compile services/hyper_ai_service.py services/hyper_ai_memory_service.py services/ai_context_compression_service.py services/ai_trading_strategy_spec_service.py tests/test_hyper_ai_llm_base_url_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_routes.py`
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py -q` returned 17 passing tests.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_llm_redirect_guard or hyper_ai_custom_endpoint_ssrf_guard or current_repo_completion_audit"` returned 3 passing tests.
- Passed: `cd backend && uv run pytest tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py -q` returned 16 passing tests.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q -k "model_adjustment_uses_profile_model or model_adjustment_sanitizes_model_output_public_fields or redacts_sensitive_exception_type or signal_gateway_payload_contract_is_stable_signal_only or failed_gateway_handoff_audit_is_non_secret or signal_detail_and_gateway_payload_redact_sensitive_fields or signal_handoff_requires_accepted_backtest_summary"` returned 8 passing tests.
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_context_compression_error_safety.py tests/test_hyper_ai_memory_error_safety.py tests/test_ai_trading_v1_completion_audit.py -q` returned 200 passing tests.
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
