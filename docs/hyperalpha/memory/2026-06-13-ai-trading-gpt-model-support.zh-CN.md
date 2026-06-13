# 2026-06-13 AI Trading Codex GPT-5.5 Local Test

## 本轮结论

- 用户纠偏：本地测试只需要接入当前 Codex 使用的 `gpt-5.5`，不要在 AI Trading 页面暴露多 provider/多模型配置。
- 本机 `~/.codex/config.toml` 已确认 Codex 当前 `model = "gpt-5.5"`。
- AI Trading 的 Hyper AI Config 弹窗已固定为 `Codex GPT-5.5` / `OpenAI` / `gpt-5.5`，页面不再展示 provider/model 下拉；本地测试只留 API key 输入。
- OpenAI provider 预设默认模型改为 `gpt-5.5`。
- Runtime readiness、model-adjust、env check、live acceptance runner、completion audit 和状态文档已同步为 Codex GPT-5.5 本地测试路径。
- 真实 Codex GPT-5.5 API key live model-adjust 未验收；真实模型调用仍必须由用户先配置 Hyper AI profile/API key，并显式运行 `--confirm-live-model-call`。

## 安全边界

- 不在前端硬编码或渲染 OpenAI API key/base URL。
- AI Trading 仍只生成策略调整/信号，不直接下单；signal-only、backtest gate、hard risk、user confirmation 和 order-backend-only 边界保留。
- Live model-adjust acceptance runner 仍默认拒绝真实模型调用；无 `--confirm-live-model-call` 时不会访问 Codex GPT-5.5。
- Unsupported provider 仍会返回安全 blocker，且 runtime 不返回 API key/base URL。

## 本地验证

- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_env_check.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_production_operator_preflight.py -q -k "strategy_signal_and_handoff_flow or runtime_reports_model_adjustment_readiness_without_secrets or strategy_spec_model_adjustment_uses_profile_model_then_safe_adjusts or model_adjustment_readiness_ui_uses_safe_blocker_labels or env_check_ready_requires_local_mock_gateway or live_model_adjust_acceptance or operator_preflight_blocks_without_external_evidence"`：11 passed。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py tests/test_ai_trading_env_check.py tests/test_ai_trading_model_adjust_live_acceptance.py -q`：110 passed。
- `cd frontend && npm run build`：通过，仅有既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size 警告。
- `scripts/local-dev/install_launch_agent.sh`：已同步并重启固定本地 runtime。
- `cd backend && AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`：返回 `ready=true`、`runtime_mirror.current=true`，model-adjust next action 为 `Create a Hyper AI model profile with Codex GPT-5.5 before model-adjust.`。
- Browser 打开 `http://127.0.0.1:5174/app/ai-trading`：不填 API key 可直接进入主界面；页面显示 `Codex GPT-5.5` 且不显示旧 `GPT/DeepSeek/Qwen` 文案；配置弹窗显示固定 `Local test model / Codex GPT-5.5 / OpenAI / gpt-5.5`，无 provider 下拉、无模型输入、无 Base URL 字段，console error/warn 为 0。

## Governance

- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation
- codex/ai-agent-multitenant-foundation
- 已 push，不 merge
- default production readiness DB-audit blocker
- scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 Codex GPT-5.5 profile/API key
