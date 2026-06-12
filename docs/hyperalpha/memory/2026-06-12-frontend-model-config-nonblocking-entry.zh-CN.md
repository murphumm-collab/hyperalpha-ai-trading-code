# 2026-06-12 Frontend Model Config Nonblocking Entry Memory

## 本轮新增

- Hyper AI 启动流程不再因为 `llm_configured=false` 打开全屏 onboarding / API-key 门禁。
- 用户未配置 DeepSeek/Qwen API key 也可以直接进入 Hyper AI / AI Trading 主页面，查看 Gateway、Agent session、Specs、Signals、Attempts、可交易标的和模型 readiness 状态。
- DeepSeek/Qwen API key 配置后置到主页面：
  - AI Trading Model 卡片里的 `Configure DeepSeek/Qwen model` 按钮继续打开现有 `Hyper AI 配置` 弹窗。
  - `Hyper AI 配置` 弹窗继续承载 provider、API key、model、custom base URL。
  - fake/invalid key 提交会停留在配置页并显示固定安全错误 label，不会白屏。
- Frontend public asset 路径从 `/static/*` 改为 Vite public-root 路径，例如 `/logo_app.png`、`/arena_logo_app_small.png`、`/binance_logo.svg`、`/arena-sprites/...`，避免进入主页面后出现静态资源 404 噪音。
- Completion audit 新增：
  - `| AI Trading frontend model-config nonblocking entry | Done |`
  - `| AI Trading frontend public asset path guard | Done |`

## 已验证

- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "model_config_is_nonblocking or frontend_public_asset_paths or root_app_has_error_boundary"`
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "frontend_model_config_nonblocking or frontend_public_asset_path or current_repo_completion_audit"`
- `cd frontend && npm run build`
- `scripts/local-dev/install_launch_agent.sh`
- `cd backend && AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current`
- Playwright: 打开 `http://127.0.0.1:5174/#ai-trading`，不填 API key 直接进入 Hyper AI / AI Trading 主页面，console error/warn 为 0。
- Playwright: 选择 Deepseek、填入 fake key 后提交，仅出现预期 `/api/hyper-ai/profile/llm` 400，页面保留在配置 UI 并显示 `HTTP 400: Model connection test failed`，没有白屏。

## 边界

- Branch: `codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。
- Local acceptance command: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`
- Default production readiness DB-audit gate remains blocked.
- default production readiness DB-audit blocker: 未提供真实生产 DB audit / 外部 evidence 前保持阻断。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部生产验收。
- 本轮不触发真实交易所请求、真实模型调用、订单后端 handoff 或 live order 解锁。
- 本轮仍保持 `ready_for_live_orders=false`；真实 macOS reboot、真实 Auth/admin 登录态和真实交易所执行仍是外部 pending。
