# 2026-06-13 AI Trading Model Readiness Sensitive Endpoint Gate

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。重点是把上一轮 Hyper AI LLM base URL 安全边界延伸到 AI Trading runtime model-adjust readiness。

## 已完成

- `services.hyper_ai_service.get_llm_config` 现在对任何 provider 的 profile `llm_base_url` 执行同一条敏感 URL fail-closed 规则；历史脏 DeepSeek/Qwen/OpenAI/custom endpoint 只返回 `[redacted_sensitive_llm_base_url]`、`configured=false`、`base_url_blocked=true`，不会静默回退到 provider preset 后继续报 ready。
- `services.ai_trading_strategy_spec_service._summarize_model_adjustment_readiness` 改为复用 `get_llm_config`，避免 AI Trading runtime 直接读取 profile 字段导致脏 endpoint 被误判为可用。
- `/api/ai-trading/runtime` 对历史脏 DeepSeek/Qwen endpoint 返回 `model_base_url_rejected_sensitive` blocker，`ready=false`，且不返回 endpoint URL 或 API key。
- Hyper AI AI Trading Model 卡片加入 `model_base_url_rejected_sensitive` 的固定安全文案 `Endpoint rejected`，继续避免 raw backend detail、endpoint 或 API key 渲染到 To C UI。
- Completion audit 新增 `| AI Trading model readiness sensitive endpoint gate | Done |` 状态 marker，防止该安全边界从 V1 本地验收文档里消失。

## 验证

- Passed: `cd backend && uv run python -m py_compile services/hyper_ai_service.py services/ai_trading_strategy_spec_service.py tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_v1_completion_audit.py -q -k "legacy_sensitive_base_url_blocks_provider_profile_even_with_preset or runtime_reports_model_adjustment_readiness_without_secrets or model_adjustment_readiness_ui_uses_safe_blocker_labels or model_readiness_sensitive_endpoint_gate or current_repo_completion_audit"` returned 5 passing tests.
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py -q` returned 100 passing tests.
- Passed: `cd frontend && npm run build` completed with only existing baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warnings.
- Passed: `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` returned `local_v1_accepted=true`, `ready_for_live_orders=false`, and no local blockers.
- Full local acceptance command remains `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`; this slice uses focused checks first and keeps the default production readiness DB-audit blocker as an expected non-live gate.

## 仍不改变

- 真实 DeepSeek/Qwen API key live model-adjust 仍未验收。
- 真实 HyperAlpha 订单后端 URL/token handoff 仍未验收。
- 真实 Auth/JWKS、生产 hard-risk、真实 admin visual、macOS 整机重启恢复仍属于外部验收。
- `ready_for_live_orders` 必须继续保持 `false`，实盘执行仍由外部订单后端和生产 evidence gate 控制。

## 分支边界

- 当前分支：`codex/ai-agent-multitenant-foundation`
- 远程目标：`origin/codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation
- 已 push，不 merge
- 不合并，不直接切到生产实盘。
- 生产实盘外部验收仍需要：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
