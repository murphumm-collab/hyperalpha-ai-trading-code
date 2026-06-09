# HyperAlpha AI Trading V1 验收清单

日期：2026-06-09

## V1 目标

V1 不是让 AI 直接实盘下单。

V1 的完成标准是：用户可以在本地/测试环境通过 AI Trading 页面完成标的选择、策略草案、自然语言调整、保存、审批、回测证据绑定、信号事件生成、拒绝/确认 handoff，并且只有通过安全检查的信号才会交给外部订单后端。

真实交易执行仍由 HyperAlpha 订单后端负责。

## 必须完成

- 多用户隔离：每个用户只能读取、调整、审批、归档、生成和 handoff 自己的 strategy spec / signal event / handoff attempt。
- 多会话 Agent：AI Trading strategy spec、signal event、handoff attempt 必须支持当前用户内的 `agent_session_id` 分区；agent session 本身可创建、重命名、更新压缩上下文和归档，并能生成非敏感 session context packet，避免一个用户的多个策略会话混在一起。
- 市场标的：Hyperliquid Crypto Top 20/50 与 HIP-3 Top 20/50 可用于策略入口，HIP-3 `dex:symbol` 身份不能丢失。
- 策略草案：支持结构化 draft、validate、save、list、detail、approve、archive。
- 策略调整：支持本地受控自然语言 adjustment，也支持 DeepSeek/Qwen model-adjust 后进入同一个安全 parser。
- 安全边界：任何 strategy spec / signal candidate 都必须保持 `signal_only`、`not_an_order`、`ai_may_place_orders=false`、`order_backend_only=true`。
- 回测前置：signal event / handoff 必须绑定 handoff-ready backtest evidence；策略调整后旧 approval/backtest 必须失效。
- 信号审计：signal preview 必须持久化成 current-user signal event，支持 detail/list/reject。
- 订单后端 handoff：默认 disabled；启用后也必须要求用户确认、未过期、信号身份一致、action/symbol 一致、回测合格、payload 契约稳定。
- 脱敏：API response、gateway payload、handoff attempt、strategy spec、backtest evidence 都不能泄露 API key、token、secret、private key、authorization。
- 前端：`/app/ai-trading` 页面必须支持完整操作流，按钮状态必须以后端 preflight 为准。
- 运营 readiness：管理员必须能通过只读、无网络、无提交的 production readiness 报告看到 Auth/JWKS、订单后端 handoff、AI stream、硬风控和模型 key policy 的上线 blocker，普通用户不能访问。
- 文档：status、memory、gateway contract、V1 checklist 必须保持最新。
- Git：只在 `codex/ai-agent-multitenant-foundation` 分支本地提交；GitHub 上传按当前用户要求暂不处理。

## 当前已验证

- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：一键本地 V1 验收通过，覆盖 backend compile、51 条 AI Trading 回归、API-level smoke、默认生产 handoff gate 阻断、默认生产总 readiness gate 阻断、frontend build、runtime readiness、live local mock handoff；最新证据为 spec `#17`、signal event `#15`、runtime `target_kind=local_mock`、`agent_sessions.total=2`。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：51 条 AI Trading/env checker/live-stack runner/production readiness/admin readiness API/mock gateway/production handoff gate 回归通过。
- `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py database/models.py database/migrations/add_ai_trading_agent_session_fields.py tests/test_ai_trading_routes.py`：通过。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q`：31 条 AI Trading route regression 通过，覆盖 first-class agent session create/update/archive、context compression persistence、archived session 禁止继续保存 strategy spec、metadata 同步到 spec/signal/handoff attempt、active/archived list 隔离，以及 Bob 不能修改/归档/压缩 Alice session。
- `cd backend && uv run python scripts/ai_trading_v1_acceptance_smoke.py`：通过，覆盖 draft -> model-adjust -> save -> attach backtest -> approve -> reject signal -> confirmed mock handoff -> runtime。
- `cd backend && uv run python scripts/ai_trading_v1_env_check.py`：在 Docker/Postgres/mock gateway/backend/frontend 启动后返回 `ready=true`，并结构化输出/校验 runtime gateway `target_kind=local_mock` 和空 `runtime_config_blockers`。
- `cd backend && uv run python scripts/ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff`：通过，覆盖本地 LaunchAgent/live Postgres 栈 draft -> save -> attach backtest -> approve -> eligible signal -> confirmed mock handoff -> attempt audit -> runtime；最新证据为 spec `#15`、signal event `#13`、gateway response `mock_accepted`。脚本默认拒绝无确认 handoff，只允许本地 URL，并要求 runtime gateway `target_kind=local_mock`。
- `cd backend && uv run python scripts/ai_trading_production_handoff_check.py --strict`：当前默认配置应拒绝生产 handoff；真实订单后端验收前必须通过该生产前检查，且不能使用 localhost/mock/placeholder URL。
- `cd backend && uv run python scripts/ai_trading_v1_production_readiness_check.py --strict`：当前默认配置应拒绝生产 readiness；真实上线前必须同时通过 Auth/JWKS、真实订单后端 handoff、AI stream 容量隔离、硬风控 TP/SL/notional/杠杆配置，并且不输出 token/API key 原文。
- `/api/ai-trading/admin/production-readiness`：本地运行时匿名请求返回 401，临时 admin bearer 返回脱敏 readiness；当前本地 mock 配置下 `production_ready=false`，13 个 blockers 覆盖真实 Auth/JWKS、生产 handoff URL、硬风控 TP/SL/notional 等未配置项，且 `token_value_returned=false`。
- 后端运行时 handoff eligibility 也会拒绝未设置 `AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true` 的外部订单后端 URL；本地 mock gateway 不要求生产审批。
- `cd frontend && npm run build`：通过，AI Trading runtime 摘要显示 Sessions 计数，Recent 区块显示 active/archived agent sessions，并能按当前 session 过滤 specs/signals；剩余为既有 browserslist/baseline/chunk-size warning。
- In-app Browser 可以打开 `http://127.0.0.1:5174/#settings`；本地 auth config disabled 时 admin tab 按设计隐藏，普通本地浏览器不能看到 admin readiness 面板。管理员登录态下的 visual check 留到真实 Auth/JWKS 配置后验收。
- In-app Browser 可以打开 `http://127.0.0.1:5174/app/ai-trading`；跳过本地 onboarding 后可渲染 Hyper AI / AI Trading 页面、Gateway/Specs/Signals runtime、`Gateway available / 15m max / Local mock`、All/Crypto/HIP-3 市场分段和 Crypto/HIP-3 标的。
- In-app Browser 已验证 agent-session UI：页面显示 `Sessions 2 active`、`Agent session` 下拉默认选中最新 `BTC V1 Live Stack Acceptance ...`、`Session name` / `Context summary` 编辑框、save/archive 图标按钮、`Recent agent sessions`、recent spec `#17` 和 recent signal `#15`。
- In-app Browser 已验证 agent-session history/context UI：选中 session 后 Recent 区块切换为 `Session specs` / `Session signals` 并只显示当前 session 的 spec `#17` / signal `#15`；`Load context` 会把 `ai_trading_agent_session_context.v1` 非敏感 context packet 回填到聊天输入；本地归档 smoke session 可在 `Archived sessions` 区块显示。
- In-app Browser 已验证 agent-session context compression UI：`Compress context` 会把当前 session 的 specs/signals/handoff blocker 压缩成可读 `AI Trading session compressed context v1` summary，写回 `Context summary` 输入框，且不会触发 `[redacted_sensitive_context]`。
- In-app Browser 已验证 HIP-3 分段过滤：`xyz:NVDA` / `xyz:AAPL` / `xyz:TSLA` 可见，BTC 不在 HIP-3 过滤结果中。
- In-app Browser 已验证 `xyz:NVDA` safe prompt fill 和 strategy draft：UI 显示 `NVDA · 15m`、`ready_for_review`、`Boundary signal only`、`Backtest not_run`、`Unsaved draft`。
- In-app Browser 已在最终代码验证 BTC 当前卡片完整安全流：draft -> natural-language adjust -> save -> approve -> inline backtest evidence -> `backtest ready` -> signal preview -> reject；证据记录为 spec `#5`、signal `#3 rejected`。
- In-app Browser 已验证 Recent signals 展示正向 mock handoff 结果：`BTC · buy`、`#2 submitted`，并可读取 handoff attempts，attempt `submitted`、`gateway_ready=true`、gateway response summary 已脱敏。
- 本地 live API 已在最终代码验证正向 mock gateway handoff：spec `#6`、signal event `#4`、`handoff_status=submitted`、latest attempt `submitted`、`gateway_ready=true`。
- Hyper AI AI Trading 当前策略卡片已改为内联 Backtest ID / Metrics JSON 输入，避免依赖浏览器原生 prompt；recent spec 行仍保留 prompt 兼容入口。
- Hyper AI AI Trading 用户动作请求已加 45s 超时恢复，避免一次网络/热更新抖动让 draft/save/approve/adjust/backtest/signal/handoff/reject 按钮永久 loading。
- LaunchAgent 本地后端已加入 `HYPERALPHA_LOCAL_DEV_LIGHT_MODE=true`，本地常驻服务跳过行情/新闻/账户快照等重后台采集，保留 AI Trading API、mock gateway 和前端验收稳定性。
- LaunchAgent `com.hyperalpha.ai-trading-local` 已固化成本地 runtime mirror 启动方式：安装脚本同步 runtime 副本到 Application Support，launchd 已在本机会话内恢复 frontend `5174`、backend `8802`、mock gateway `5621`，env checker 返回 `ready=true`。

## 当前未验收

- 实际 macOS 整机重启后的自动恢复还未物理验收；当前已完成 LaunchAgent 会话内自恢复验收。后续代码变更需要重跑 `scripts/local-dev/install_launch_agent.sh` 同步 runtime 副本。
- 真实 DeepSeek/Qwen API key live model-adjust 未验收；当前为 mocked Qwen regression。
- 真实 HyperAlpha 订单后端 URL/token live handoff 未验收；当前为 disabled-by-default 和 mock gateway contract 验收。
- 生产 handoff readiness gate 和生产总 readiness gate 已实现，但真实 HTTPS 订单后端 URL/token、真实 Auth/JWKS、硬风控生产值和 `AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true` 的 live 验收未做。
- Settings Admin production readiness 面板代码和 build 已完成；真实登录态/真实 Auth 配置下的可视化验收未做。本地 auth disabled 时 admin tab 隐藏是预期状态。
- AI Trading agent session 后端/API/UI 已完成 first-class create/update/archive、当前 session 选择、归档列表、context packet 载入和按 session 过滤 specs/signals；独立 full-page session 详情页尚未做。
- 真实交易所执行不属于 V1 本地验收完成条件，必须另开生产实盘验收。

## V1 通过标准

- 一键本地验收 runner 通过：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 后端 AI Trading 回归通过。
- 生产总 readiness 默认阻断且测试通过：`cd backend && uv run python scripts/ai_trading_v1_production_readiness_check.py --strict`。
- API-level V1 smoke runner 通过：`cd backend && uv run python scripts/ai_trading_v1_acceptance_smoke.py`。
- 环境 readiness 可检查：`cd backend && uv run python scripts/ai_trading_v1_env_check.py`。
- 本地 live-stack mock handoff 可复跑：`cd backend && uv run python scripts/ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff`。
- 前端 build 通过。
- Postgres/Snapshot DB 启动后，后端 `/api/ai-trading/runtime` 可响应。
- 浏览器从 `/app/ai-trading` 完成至少一条测试策略流：draft -> adjust -> save -> approve -> attach/run backtest evidence -> create signal event -> reject 一条 signal -> confirm handoff 一条 eligible mock gateway signal。
- Handoff payload 符合 `docs/hyperalpha/ai-trading-signal-gateway-contract.md`。
- Mock gateway 可用：`cd backend && uv run uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1`，主后端 `AI_TRADING_SIGNAL_GATEWAY_URL` 指向 `http://127.0.0.1:5621/api/ai-trading/signals`。
- Status 和 memory 文档标记通过证据。
