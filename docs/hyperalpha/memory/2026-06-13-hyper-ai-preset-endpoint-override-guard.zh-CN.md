# 2026-06-13 Hyper AI Preset Endpoint Override Guard

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。本轮目标是收紧 Hyper AI LLM 配置入口：DeepSeek/Qwen/OpenAI 等 preset provider 不应接受用户/API 传入的自定义 `base_url` override，只有 `custom` provider 可以自定义 endpoint。

## 已完成

- `/api/hyper-ai/test-connection` 和 `/api/hyper-ai/profile/llm` 对非 `custom` provider 的非空 `base_url` 返回固定错误 `llm_base_url_not_allowed_for_preset_provider`，并且在网络连接测试和 profile 保存前停止。
- `services.hyper_ai_service.test_llm_connection` 现在对 preset provider 总是使用 provider preset endpoint，忽略直接调用时传入的 `base_url` override。
- `services.hyper_ai_service.save_llm_config` 现在只为 `custom` provider 保存经过校验的 `llm_base_url`，preset provider 保存时会清空 override。
- 既有 custom provider base URL 敏感值拒绝、legacy 污染 endpoint redaction、AI Trading model readiness sensitive endpoint gate 不变。

## 验证

- Passed: `cd backend && uv run python -m py_compile api/hyper_ai_routes.py services/hyper_ai_service.py tests/test_hyper_ai_llm_base_url_safety.py`
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py -q` returned 9 passing tests.
- Passed: `cd backend && uv run python -m py_compile api/hyper_ai_routes.py services/hyper_ai_service.py tests/test_hyper_ai_llm_base_url_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "preset_endpoint_override or hyper_ai_llm_base_url_safety or current_repo_completion_audit"` returned 12 passing tests.
- Passed: `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` returned `local_v1_accepted=true`, `ready_for_live_orders=false`, and no local blockers.

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
