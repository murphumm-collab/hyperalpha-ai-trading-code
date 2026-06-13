# 2026-06-13 AI Trading GPT Model Support

## 本轮结论

- AI Trading V1 model-adjust 已把 OpenAI/GPT 纳入受支持 provider；当前允许 `openai`、`deepseek`、`qwen`。
- OpenAI provider 预设默认模型改为 `gpt-4o`，避免用户选择 OpenAI 后默认进入非 GPT 命名模型。
- AI Trading 页面和 onboarding 的模型配置入口文案已更新为 GPT/DeepSeek/Qwen；不配置 API key 仍可进入页面，API key 继续在 Hyper AI LLM Config modal 内后置配置。
- Runtime readiness、model-adjust、env check、live acceptance runner、completion audit 和 production model policy 已同步 GPT/DeepSeek/Qwen provider 范围。
- 真实 GPT/DeepSeek/Qwen API key live model-adjust 未验收；真实模型调用仍必须由用户先配置 Hyper AI profile/API key，并显式运行 `--confirm-live-model-call`。

## 安全边界

- 不在前端硬编码或渲染 OpenAI API key/base URL。
- AI Trading 仍只生成策略调整/信号，不直接下单；signal-only、backtest gate、hard risk、user confirmation 和 order-backend-only 边界保留。
- Live model-adjust acceptance runner 仍默认拒绝真实模型调用；无 `--confirm-live-model-call` 时不会访问 GPT/DeepSeek/Qwen。
- Unsupported provider 仍会返回安全 blocker，且 runtime 不返回 API key/base URL。

## 本地验证

- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_env_check.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_operator_preflight.py -q -k "strategy_signal_and_handoff_flow or runtime_reports_model_adjustment_readiness_without_secrets or strategy_spec_model_adjustment_uses_profile_model_then_safe_adjusts or model_adjustment_readiness_ui_uses_safe_blocker_labels or env_check_ready_requires_local_mock_gateway or live_model_adjust_acceptance or operator_preflight_blocks_without_external_evidence"`：11 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_env_check.py tests/test_ai_trading_model_adjust_live_acceptance.py -q`：110 passed。
- `cd frontend && npm run build`：通过，仅有既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size 警告。
- `scripts/local-dev/install_launch_agent.sh`：已同步并重启固定本地 runtime。
- `cd backend && AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`：`ready=true`，runtime mirror current，model-adjust next action 已显示 OpenAI/GPT, DeepSeek, or Qwen。
- Browser 验证：`http://127.0.0.1:5174/app/ai-trading` 显示 GPT/DeepSeek/Qwen setup copy；配置弹窗里选择 OpenAI 后模型输入为 `gpt-4o`；未保存 API key；console error/warn 为空。

## Governance

- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation
- codex/ai-agent-multitenant-foundation
- 已 push，不 merge
- default production readiness DB-audit blocker
- scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 GPT/DeepSeek/Qwen profile/API key
