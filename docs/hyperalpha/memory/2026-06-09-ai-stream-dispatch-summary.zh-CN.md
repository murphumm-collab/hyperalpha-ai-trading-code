# HyperAlpha AI Trading 开发压缩记忆

版本：v0.2  
日期：2026-06-09  
分支：`codex/ai-agent-multitenant-foundation`

## 1. 当前产品边界

- 目标是在 `app.hyperalpha.org` 上把 Vibe-Trading/Hyper AI 能力改造成 To C 可用的 AI Trading Agent。
- 第一版重点是 Hyperliquid 可交易标的、DeepSeek/Qwen 模型、多用户隔离、回测/策略信号和安全执行前置。
- 真实下单仍由现有交易后端负责；AI 只进入策略建议、策略编辑、诊断、信号候选、风险解释和需要确认的工具调用链。
- 用户 API key、钱包私钥、交易凭据不进入 AI 上下文。
- 最新 AI Trading 策略草案契约是 `signal_only`：AI 可以生成/校验结构化策略 spec，但不能直接下单。

## 2. 已实现安全基础

- Hyper AI、Prompt AI、Signal AI、Program AI、Attribution AI、Kline AI 的主要服务入口已要求 `user_id`，缺失用户上下文时 fail closed。
- Hyper AI profile、memory、conversation、skill/tool settings 已按用户隔离。
- Prompt/Signal/Program/Attribution shared tools 已按当前用户过滤账号、策略、信号池、prompt、program、decision log 和 analytics 数据。
- Hyperliquid/Binance 钱包、手动交易、策略执行、Program Trader、AI Trader 执行路径已传递 account owner，避免跨用户读写交易配置。
- 自动 AI Trader 和 Program Trader 下单前已接入 hard risk validator。
- 前端主要 AI chat、stream polling、Settings、交易账户、Signal/Prompt/Program/Attribution 等请求已改为 auth-aware fetch。
- `/api/ai-trading/strategy-spec/schema|draft|validate` 已提供结构化 Hyperliquid 策略草案和校验入口，默认要求用户审批、止盈/止损、最大亏损和 no-direct-order 边界。
- Hyper AI 右侧 AI Trading 标的区域已增加结构化策略草案入口，草案会回填聊天框供 agent 审核。
- `ai_trading_strategy_specs` 已持久化当前用户的策略 spec 草案/待审/已审批记录；审批会重新校验 spec，不触发下单或信号发送。
- Hyper AI 策略草案摘要已提供保存和审批按钮，仍只操作 review 状态。
- 已审批 strategy spec 可生成 `hyperalpha.ai_trading.signal_candidate.v1` 信号预览；该 preview 明确 `not_an_order=true`、`ai_may_place_orders=false`，只供聊天审核和后端 handoff 前检查。
- Hyper AI 已审批草案摘要可把 signal preview 回填到聊天框，不会提交执行网关。
- `ai_trading_signal_events` 已持久化当前用户的信号候选审计记录，默认 `status=review_candidate`、`handoff_status=not_submitted`。
- Hyper AI signal preview 按钮现在会先创建 signal event，再把候选 JSON 回填聊天框。
- `/api/ai-trading/signal-events/{id}/handoff` 已实现外部订单后端 handoff 边界，但默认 `AI_TRADING_SIGNAL_GATEWAY_ENABLED=false`，未配置时返回 409 不发送。
- gateway 只提交已审计、仍带 `not_an_order` / `ai_may_place_orders=false` 边界的 signal event；URL/token 只发给订单后端，不进入 AI model。
- `/api/ai-trading/runtime` 已返回非敏感运行状态：gateway 是否启用/URL 是否配置，以及当前用户 strategy spec / signal event 计数。
- Hyper AI AI Trading 面板会显示 Gateway / Specs / Signals 运行摘要，保存、审批、创建信号事件后刷新。
- Hyper AI AI Trading 面板现在会列出最近保存的 strategy specs 和最近创建的 signal events；用户可以把任一记录详情回填到聊天框，让 agent 做风控/止盈止损/执行边界复核，不会提交订单。
- Recent signal events 现在有 gateway-gated handoff 按钮：只有 runtime 显示 gateway 已启用且 URL 已配置、事件仍是未提交 `review_candidate` 时才可点；点击仍走后端 `/handoff` 边界，不绕过默认关闭策略。
- Signal event list/detail responses 现在包含非敏感 `handoff_eligibility`：会说明 gateway 未启用、URL 未配置、事件状态不对、已提交、signal 不适合 handoff、或缺少 `not_an_order` / `order_backend_only` 等 blocker；前端按钮优先使用这个 preflight。
- `/api/ai-trading/runtime` 现在汇总 review-candidate handoff readiness：`review_candidates`、`eligible`、`blocked` 和 `by_blocker`；Hyper AI 面板的 Signals 卡片显示 total / ready。
- 新增 `ai_trading_signal_handoff_attempts`：每次 handoff 尝试如果 blocked、failed 或 submitted 都会写非敏感审计记录，包含 blockers、eligibility、gateway_ready、result，但不包含 gateway URL/token 或交易凭据；`GET /api/ai-trading/signal-events/{id}/handoff-attempts` 可按当前用户读取。
- Hyper AI AI Trading recent signals 行现在有只读 handoff history 按钮，会读取 `/handoff-attempts` 并把 attempts JSON 回填聊天框给 agent 做审计复核，不会触发执行。
- 新增 signal event reject 流程：`POST /api/ai-trading/signal-events/{id}/reject` 只允许拒绝 `review_candidate`，会把 signal JSON 标为 `rejected_by_user`、`eligible_for_backend_handoff=false`、`handoff_status=rejected`；Hyper AI recent signals 行有拒绝按钮，拒绝后回填聊天框供 agent 复核。
- 持久化 signal event 时会把 signal JSON 的 `idempotency_key` 改成事件级 `signal_event:{id}`，并写入 `signal_event_id`；gateway payload 顶层 idempotency key 复用同一个值，避免同一 strategy spec 生成多个候选信号时共享 preview key。
- Hyper AI recent signals 行现在显示 Ready / Blocked / Rejected / Submitted 状态 badge；blocked 时会展示第一条 blocker，减少用户盲点操作。
- AI Trading FastAPI route 回归现在覆盖 Alice/Bob 两个用户共享同一数据库时的隔离：Bob 不能 list/read/approve/archive/preview/create/reject/handoff Alice 的 strategy spec、signal event 或 handoff attempt。
- 新增 `/api/ai-trading/market-universe`：返回 Hyperliquid Crypto Top 20/50 和 HIP-3 Top 20/50 presets，包含 dex、`coin`/`exchange_symbol`、category、24h volume、OI、max leverage、only-isolated、source/errors 等非敏感市场元数据。
- Hyper AI AI Trading 标的加载逻辑现在优先使用用户 watchlist；没有 watchlist 时使用 AI Trading market universe 的 crypto + HIP-3 presets；最后才 fallback 到 available symbols。
- Strategy spec 和 signal candidate 现在保留 HIP-3 market identity：`market.dex`、`market.exchange_symbol`（如 `xyz:NVDA`）、`market.display_symbol`、category；内部 `symbol` 仍可保持 `NVDA` 用于既有记录索引。
- Strategy spec 和 signal candidate 现在记录非敏感 `ai_model` 上下文：`provider`、`model`、`source`、是否为 V1 DeepSeek/Qwen provider；校验会 warning 缺失/非 V1 provider，并 reject `api_key`、`token`、`secret` 等字段进入 `ai_model`。
- Hyper AI AI Trading strategy draft 请求现在携带当前 profile 的 `llm_provider/llm_model`，来源标记为 `hyper_ai_profile`；不携带 base URL、API key 或 token。
- 新增 `/api/ai-trading/strategy-specs/{id}/backtest-summary`，用于把当前用户的 backtest summary 绑定到 strategy spec；这不是完整回测引擎，只是把外部/未来 Backtest Service 的结果作为 handoff 前置证据落库。
- Signal candidate 会复制生成当时的 `backtest` 摘要；handoff eligibility 要求 passing/accepted backtest summary，否则即使 gateway enabled 也 blocked。事后补回测不会改变旧 signal event，必须重新生成候选信号。
- Hyper AI AI Trading strategy 卡片现在显示 backtest readiness，并提供 chart 图标 action 让用户输入外部 backtest id 和 metrics JSON，提交到 `/backtest-summary`；该 UI 仍不运行真实回测、不触发订单。
- 新增 `/api/ai-trading/strategy-specs/{id}/backtest-result`，用于把当前用户已有的 Program BacktestResult 绑定到 AI Trading strategy spec；后端会通过 account/program binding 做 owner guard，并自动把 total return、max drawdown、trade count、win rate、profit factor、Sharpe 等持久化指标映射进 backtest gate。
- Hyper AI AI Trading strategy 卡片和 recent spec 行现在有 link 图标 action，可输入已有 Program Backtest result ID 绑定 evidence；不会运行订单，也不会手填 metrics。
- 新增 `/api/ai-trading/backtest-results`，返回当前用户可绑定的 Program BacktestResult 候选列表，支持 `status`、`symbol`、`limit`，返回 symbol、program/account 名称、关键 metrics、handoff_ready，但不返回 Program code、API key 或交易凭据。
- Hyper AI AI Trading panel 现在会列出最近 completed Program Backtests，用户可以点 link 图标把某条 handoff-ready evidence 绑定到当前 strategy spec；如果当前草案未保存，会先保存再绑定。

## 3. AI Stream / Worker 现状

- `ai_stream_tasks` / `ai_stream_chunks` 持久化 background stream task 和 chunk，支持服务重启后的轮询恢复。
- 本地 admission 支持全局和单用户并发限制：`AI_STREAM_MAX_RUNNING_GLOBAL`、`AI_STREAM_MAX_RUNNING_PER_USER`。
- 可选 Redis distributed admission 支持多实例共享并发 lease。
- high-risk confirmation 已持久化到 `ai_stream_confirmations`，允许用户确认提交到不同后端实例后唤醒运行中的 task。
- `ai_stream_tasks.runner_id` 和 `last_heartbeat_epoch` 记录执行实例与心跳。
- `ai_stream_dispatch_jobs` 已作为 serializable worker queue：pending / claimed / running / completed / failed。
- 可选 dispatch worker 能 claim 注册 task type，并把生成器输出写回统一 stream buffer。
- 已接入 serializable task handler：
  - `hyper_ai.chat`
  - `hyper_ai.onboarding`
  - `prompt_ai.chat`
  - `signal_ai.chat`
  - `program_ai.chat`
  - `attribution_ai.chat`
- `AI_STREAM_DISPATCH_CLAIM_STALE_SECONDS` 用于恢复 claimed 但未进入 running 的 job：
  - attempts 未耗尽：重新回到 pending；
  - attempts 已耗尽：dispatch job failed，同时 stream task 标记 error。
- stream error 解析已兼容 `message`、`content`、`error`、`text`、`raw` 和非 dict payload，避免任务失败原因变成 `Unknown error`。

## 4. 上下文压缩与记忆

- `ai_context_compression_service.py` 负责 token 估算、tool-call group 边界保护、conversation summary、compression points 和 tool call restoration。
- Hyper/Prompt/Signal/Program/Attribution AI 服务均已调用 compression pipeline。
- `compress_messages(..., user_id=...)` 已把当前用户传给 background memory extraction。
- `hyper_ai_memory_service.py` 已按 `user_id` 存取、去重、更新、软删除 memory。
- 当前 memory categories 包含通用类别 `preference`、`decision`、`lesson`、`insight`、`context`，以及 AI Trading 专用类别 `strategy_memory`、`risk_memory`、`performance_memory`、`execution_memory`。
- Hyper AI tool schema 和 system prompt 已指导 agent 把策略逻辑、风控约束、表现结论和执行经验分别写入对应 memory category。

## 5. 已验证

- Backend compile：相关 AI stream、Prompt/Signal/Program/Attribution route 均通过 system Python 和 `uv run python -m py_compile`。
- Dispatch queue foundation smoke：enqueue、duplicate enqueue、type-scoped claim、running/completed/failed transitions、admin stats 均通过。
- Dispatch worker fake-handler smoke：claimed job 可被 runner adopt，chunk 写入 stream buffer，task/dispatch completed。
- Hyper AI dispatch enqueue smoke：chat/onboarding 在 dispatch enabled 时写入 pending job。
- Prompt/Signal/Program/Attribution dispatch static check：task type 常量和 handler registration 均存在。
- Stale claimed recovery smoke：SQLite 环境下 exhausted job 失败并同步 stream task，attempts 未耗尽 job 可重新 claim。
- Frontend production build 已通过，Settings AI Runtime 显示 dispatch queue counts 和 claim timeout。
- AI Trading strategy spec service/route smoke：完整草案进入 `ready_for_review`，缺失 TP/SL 返回 `needs_user_input`，篡改 `ai_may_place_orders=true` 会被拒。
- Frontend production build 已通过，Hyper AI AI Trading strategy-spec 草案控件编译成功。
- AI Trading strategy spec persistence smoke：SQLite 下 save/list/get/approve/archive 完成，归档记录默认列表隐藏。
- AI Trading strategy spec HTTP CRUD smoke：FastAPI TestClient 下 endpoints 保存、详情、审批、归档均通过。
- Frontend production build 已通过，Hyper AI strategy spec 保存/审批控件编译成功。
- AI Trading signal preview route smoke：未审批 spec 返回 400；审批后生成 not-an-order signal candidate，保留 mark price 等 market context。
- Frontend production build 已通过，Hyper AI signal preview 控件编译成功。
- AI Trading signal event route smoke：未审批 spec 不能创建 event，审批后可创建/list/detail 当前用户 review candidate，signal JSON 保持 not-an-order。
- Frontend production build 已通过，Hyper AI signal preview 控件已改为 auditable signal-event endpoint。
- AI Trading signal handoff route smoke：默认关闭返回 409；mock enabled gateway 后提交 `AI_TRADING_SIGNAL_CANDIDATE`，event 状态变为 submitted，并携带 bearer token 给 gateway。
- AI Trading runtime route smoke：空状态不泄露 URL/token；创建 approved spec 和 review signal event 后计数正确。
- Frontend production build 已通过，Hyper AI AI Trading runtime status 面板编译成功。
- Hyper AI memory category smoke：SQLite 下四个 AI Trading 专用 memory category 可保存和按用户读取。
- `backend/tests/test_ai_trading_routes.py` 已作为 pytest 回归，覆盖 strategy draft/save/approve、signal event、disabled gateway 409、mock enabled handoff 和 runtime counts。
- Frontend production build 已通过，Hyper AI AI Trading recent specs/signals 审计面板编译成功。
- `backend/tests/test_ai_trading_routes.py` 在 recent records UI 后重新通过。
- Playwright 已打开 `http://127.0.0.1:5174/app/ai-trading`，等待 splash fallback 后确认 Hyper AI / AI Trading shell 可渲染；因为本地 backend/Postgres 未运行，最近记录列表和 inspect 点击只能等 live API 恢复后验收。
- Frontend production build 已通过，recent signal events 的 handoff 按钮编译成功。
- `backend/tests/test_ai_trading_routes.py` 在 handoff UI 后重新通过。
- Playwright 已再次打开 `http://127.0.0.1:5174/app/ai-trading`，确认 Hyper AI / AI Trading shell 可渲染；因为本地 backend/Postgres/gateway 未运行，handoff 按钮点击验收仍待 live API。
- Python syntax compile 已通过，AI Trading service/routes 在 handoff preflight 后正常。
- `backend/tests/test_ai_trading_routes.py` 已覆盖 disabled gateway blocker、gateway enabled 后 eligible、submitted 后重复 handoff 被 blocker 禁止。
- Frontend production build 已通过，recent signal handoff 按钮已改为优先使用后端 `handoff_eligibility`。
- Playwright 已再次确认 `http://127.0.0.1:5174/app/ai-trading` 可过 splash fallback 渲染到 Hyper AI / AI Trading shell；preflight UI 点击验收仍待本地 backend/Postgres 和持久化 signal events。
- `backend/tests/test_ai_trading_routes.py` 已覆盖 runtime readiness：gateway disabled 时 0 ready/1 blocked，gateway enabled 后 1 ready，submitted 后 review candidates 归零。
- Frontend production build 已通过，Signals runtime 卡片显示 total / ready 编译成功。
- Python syntax compile 已通过，AI Trading handoff attempt model/migration/service/routes 正常。
- `backend/tests/test_ai_trading_routes.py` 已覆盖 disabled gateway 产生 blocked attempt、enabled gateway 产生 submitted attempt，并确认 attempt response 不泄露 gateway token/URL。
- Frontend production build 已通过，recent signal handoff history 只读按钮编译成功。
- `backend/tests/test_ai_trading_routes.py` 在 handoff history 前端集成后重新通过。
- Python syntax compile 已通过，AI Trading service/routes 在 signal reject 后正常。
- `backend/tests/test_ai_trading_routes.py` 已覆盖 signal event reject、rejected 后不能 handoff、runtime rejected 计数。
- Frontend production build 已通过，recent signal reject 按钮编译成功。
- `backend/tests/test_ai_trading_routes.py` 已覆盖同一 strategy spec 的多个 persisted signal events 使用不同 event-scoped idempotency key，gateway payload 和 signal JSON key 一致。
- Frontend production build 已通过，recent signal 状态 badge 和 blocker 摘要编译成功。
- `backend/tests/test_ai_trading_routes.py` 在 recent signal 状态 UI 后重新通过。
- `backend/tests/test_ai_trading_routes.py` 已新增多用户隔离回归：同一 SQLite DB 下 Alice/Bob 的 strategy specs、signal events、signal previews、reject、handoff 和 handoff-attempt audit reads 均按当前用户 404/空列表隔离。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` 曾在多用户隔离切片后通过。
- `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py` 已通过。
- `backend/tests/test_ai_trading_routes.py` 已新增 market-universe 回归：fake Hyperliquid core/HIP-3 metadata 下，crypto 按成交量排序、delisted 被过滤、HIP-3 返回 `xyz:` exchange symbol，并生成 top presets。
- `backend/tests/test_ai_trading_routes.py` 已新增 HIP-3 market identity 回归：`xyz:NVDA` draft/save/approve/signal-event 后，signal payload 保留 `exchange_symbol=xyz:NVDA` 和 `market.dex=xyz`。
- `backend/tests/test_ai_trading_routes.py` 已新增 model-context 回归：DeepSeek/Qwen provider/model 写入 spec/signal；`ai_model.api_key` 这类敏感字段会让 validation invalid。
- `backend/tests/test_ai_trading_routes.py` 已新增 backtest gate 回归：missing backtest 的 signal event 在 gateway enabled 下仍 blocked；补 passing backtest 后旧事件仍 blocked，新事件才 eligible；Bob 不能给 Alice spec 挂 backtest summary。
- `backend/tests/test_ai_trading_routes.py` 已新增 backtest metrics quality 回归：即使 backtest summary 标记 `passed`/`accepted_for_handoff=true`，缺少正交易数、最大回撤、表现指标时，gateway enabled 也不能 handoff，且不会调用订单后端。
- `backend/tests/test_ai_trading_routes.py` 已新增 Program Backtest bridge 回归：当前用户 owned Program BacktestResult 可绑定并让新 signal 在 gateway enabled 后 eligible；Bob 不能把 Alice 的 BacktestResult 绑定到 Bob 的 spec。
- `backend/tests/test_ai_trading_routes.py` 已新增 Program Backtest evidence-list 回归：列表只返回当前用户 backtest candidates，支持 symbol filter，返回 handoff_ready，不泄露 API key 或 Program code。
- `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` 已通过，当前 9 条 AI Trading route 回归全绿。
- `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py` 已通过。
- `cd frontend && npm run build` 已通过；Vite 只提示既有 browserslist/baseline 数据过旧和大 chunk 警告。最近一次通过是在 Hyper AI recent Program Backtests evidence list/direct attach action 后。
- `curl -I --max-time 3 http://127.0.0.1:5174/app/ai-trading` 返回 200；当前 Node REPL 无法解析 `playwright` 包，因此本轮没有做点击级浏览器自动化。

## 6. 未验收 / 阻塞

- 本地 PostgreSQL 未运行，导致后端 `8000` 未监听；analytics route runtime import 会因 snapshot DB 默认 Postgres 不可达而失败。
- `git push -u origin codex/ai-agent-multitenant-foundation` 仍被 HTTPS 凭据阻塞：`could not read Username for 'https://github.com': Device not configured`；本机也没有 `gh` CLI。
- live distributed worker acceptance 还需要真实 Postgres、Redis、模型凭据和至少两个 runner 实例。
- real Casdoor JWKS / issuer / audience 环境值仍需 live token 验收。
- AI Trading signal gateway live acceptance 需要真实 HyperAlpha 订单后端 URL/token；当前只做 disabled-by-default 和 mock gateway 验收。
- real exchange execution acceptance 未做；当前实现是安全基础、队列、风控和信号/agent 链路，不做实盘下单验收。
- 完整 AI Trading Hyperliquid 一键 backtest engine 和 rich backtest result UI 仍未实现；当前已实现 manual/external summary gate 和 existing Program BacktestResult evidence bridge。
- strategy spec / signal preview / signal event / recent records inspect / signal-event handoff 的浏览器点击验收仍需本地 backend/Postgres 正常运行并返回 Hyperliquid symbols、持久化记录与 gateway readiness；当前只做了页面 shell、service、persistence、FastAPI route、pytest 回归和前端 production build。

## 7. 当前提交锚点

- `463c669 feat: show ai dispatch claim timeout`
- `436108b feat: recover stale ai dispatch claims`
- `71114d7 fix: preserve ai stream error details`
- `f6d3f4a feat: dispatch remaining ai stream chat tasks`
- `6122707 feat: run hyper ai tasks via dispatch worker`
- `43d69b1 feat: add ai stream dispatch queue foundation`
