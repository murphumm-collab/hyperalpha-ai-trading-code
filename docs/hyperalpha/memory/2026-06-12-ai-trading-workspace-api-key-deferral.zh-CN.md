# 2026-06-12 AI Trading 工作区 API-key 后置配置记忆

## 本轮目标

- 用户反馈“不配置 API key 没办法进入后面页面”，要求把 API key 配置放到后面页面里。
- 本地验证 `/app/ai-trading` 已能未配置 DeepSeek/Qwen API key 进入，但配置入口主要在右侧面板；本轮把入口加到中心工作区顶部，并让配置弹窗未配置状态下明确提供“稍后配置”关闭动作。

## 已完成

- `frontend/app/components/hyper-ai/HyperAiPage.tsx`
  - 在 Hyper AI / AI Trading 中心工作区顶部新增 `data-testid="ai-trading-model-config-workspace-entry"`。
  - 未配置模型时显示 `AI Trading 模型`、后置配置提示和 `配置 API key` 按钮。
  - 点击工作区按钮打开现有 `LLMConfigModal`，没有新增 API key/base URL 渲染面。
  - `LLMConfigModal` 的取消按钮新增 `data-testid="ai-trading-model-config-later-button"`；未配置状态显示 `稍后配置`，可关闭弹窗继续留在后面页面。
- `frontend/app/locales/en.json` / `frontend/app/locales/zh.json`
  - 新增 `aiTradingModelSetup`、`aiTradingConfigureApiKey`、`aiTradingUpdateApiKey`、`aiTradingConfigureLater`、`aiTradingConfigureLaterHint`。
- `backend/tests/test_ai_trading_frontend_readiness_source.py`
  - 扩展 `test_hyper_ai_main_page_always_exposes_model_api_key_config_entry`，source guard 现在要求工作区入口、工作区按钮、`稍后配置` 按钮和安全文案都存在。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 更新 `AI Trading frontend main-page API-key config entry` marker 文案，覆盖中心工作区和右侧面板。
  - 追加本轮 focused checks、build、runtime mirror sync、browser 验证证据。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 API-key deferral 验收说明，明确先进入页面，之后从工作区顶部/右侧 Model 卡片/配置弹窗后置配置。

## 验证

- `cd backend && uv run python -m py_compile tests/test_ai_trading_frontend_readiness_source.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "model_api_key_config_entry or model_config_is_nonblocking or onboarding_defers_api_key"`：3 passed。
- `cd frontend && npm run build`：通过，仅有既有 baseline-browser-mapping / Browserslist / dynamic-import / chunk-size warning。
- `scripts/local-dev/install_launch_agent.sh`：已同步并重启本地 LaunchAgent runtime mirror。
- `cd backend && AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`：`ready=true`，`runtime_mirror.current=true`。
- Browser 验证 `http://127.0.0.1:5174/app/ai-trading`：
  - 未配置 API key 直接进入 Hyper AI / AI Trading 主页面。
  - 中心工作区显示 `AI Trading 模型` 和 `配置 API key`。
  - 点击后打开现有 Hyper AI Config modal。
  - `稍后配置` 按钮可关闭弹窗，不离开页面。

## 未改变

- 没有触碰订单后端、交易执行、DeepSeek/Qwen 真实 API key 验收或生产 readiness gate。
- 真实 DeepSeek/Qwen key、真实订单后端、真实 Auth/admin 视觉验收仍属于外部生产验收项。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；后续提交仍只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 一键验收标准仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen 和生产审批 evidence 完整通过。
