# 2026-06-12 Frontend Onboarding API-key Deferral Memory

## 本轮新增

- Legacy `HyperAiOnboarding` 默认首屏不再展示 provider/API-key/model 配置表单，也不再要求用户先填 DeepSeek/Qwen API key 才能进入后续页面。
- 默认首屏改为直接进入 Hyper AI / AI Trading 的 entry action；API key 配置保留在后续 Hyper AI / AI Trading 主页面的 Model 卡片和 `Hyper AI 配置` 弹窗里。
- 用户如果在 legacy onboarding 首屏主动点击 optional model setup，仍可打开旧 model/API-key 表单；该表单继续使用安全错误 formatter，且仍可跳过进入系统。
- Completion audit 新增 marker：
  - `| AI Trading frontend onboarding API-key deferral | Done |`

## 已验证

- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "onboarding_defers_api_key or model_config_is_nonblocking or onboarding_uses_safe_model"` returned 3 passing tests.
- `cd frontend && npm run build` passed with existing baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warnings only.

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
