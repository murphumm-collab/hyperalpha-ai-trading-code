# HyperAlpha AI Trading 完整开发方案

版本：v0.1  
日期：2026-06-08  
目标域名：`app.hyperalpha.org`  
基础方向：基于 Vibe-Trading / Hyper-Alpha-Arena 思路，将 AI Trading Agent 整合到现有 HyperAlpha 前端、后端、交易发送系统中。

## 1. 一句话目标

在现有 HyperAlpha 平台中加入一个安全可控的 AI Trading Agent：

- 用户可以用自然语言创建和调整策略。
- 系统可以基于 Hyperliquid 数据做回测。
- AI 可以生成交易方案、约束条件和结构化交易信号。
- 前端负责展示、确认、暂停和监控。
- 后端负责用户隔离、风控校验、信号审计和下单协调。
- 现有交易发送后端仍然是唯一真实下单入口。

核心原则：

```text
AI 不直接下单。
AI 不读取用户 API key。
AI 不跨用户读取上下文。
AI 只输出策略、回测请求、诊断和信号候选。
所有信号必须经过后端风控，再交给现有下单系统。
```

## 2. 已知前提

### 已有能力

- `app.hyperalpha.org` 已有用户账号系统。
- 用户下单配置和 API key 管理已存在。
- 真实下单后端已存在。
- 后端交易发送链路不需要 AI 模块直接处理。
- 可使用 DeepSeek 或 Qwen 作为模型。
- 第一版直接面向实盘，但亏损额度由平台/用户控制。
- 第一版交易数据使用 Hyperliquid 数据。
- 标的范围优先做交易量最大的 crypto 和 HIP-3 美股/指数标的 Top 20 / Top 50。

### 可复用开源能力

Vibe-Trading 适合复用：

- AI 策略生成思路。
- 回测报告结构。
- Agent session / SSE streaming 思路。
- 策略分析、指标、交易明细展示思路。

Hyper-Alpha-Arena 适合做主框架参考：

- AI Trader / Program Trader 概念。
- Hyperliquid 交易平台定位。
- 多模型 OpenAI-compatible 适配思路。
- 因子、信号、回测、实盘监控产品结构。

## 3. 最短安全路径

第一阶段不要做大而全，只打通这个闭环：

```text
用户自然语言创建策略
  -> AI 生成结构化 Strategy Spec
  -> 用户确认
  -> 回测
  -> 用户启用策略
  -> 策略运行服务定时读取行情
  -> AI 生成 Signal Candidate
  -> 后端风控校验
  -> 发送给现有交易后端
  -> 前端展示订单/持仓/执行状态
```

MVP 只做：

- 模型：DeepSeek、Qwen。
- 标的：Hyperliquid crypto Top 20 + HIP-3 US/RWA Top 20，后续扩展 Top 50。
- 周期：5m、15m、1h。
- 策略：自然语言生成 + 参数化约束。
- 回测：必须做。
- 实盘：AI 信号到后端，后端风控后下单。
- 页面：AI Trading、Markets、Strategy Detail、Backtest Result、Live Signals。

MVP 不做：

- 高频交易。
- 任意用户代码生产执行。
- 多交易所。
- 社交跟单。
- 排行榜。
- 复杂 portfolio optimizer。
- AI 直接下单。

## 4. 总体架构

```text
Frontend: app.hyperalpha.org
  -> API Backend
    -> Agent Gateway
      -> AI Agent Service
        -> DeepSeek / Qwen
    -> Backtest Service
    -> Market Data Service
    -> Strategy Runtime Worker
    -> Risk Validator
    -> Signal Gateway
      -> Existing Trading Backend
        -> Hyperliquid
```

### 服务职责

#### Frontend

- 展示 AI Agent 对话。
- 展示策略草案、策略 diff、回测结果、实时信号。
- 允许用户确认、启用、暂停策略。
- 只调用 HyperAlpha API Backend。
- 不直接访问 DeepSeek/Qwen。
- 不直接访问 Hyperliquid。
- 不直接发送订单。

#### API Backend

- 用户鉴权。
- 多用户/多策略隔离。
- 保存策略、回测、信号、执行事件。
- 组装 AI 上下文。
- 调用 AI Agent Service。
- 调用 Backtest Service。
- 调用 Risk Validator。
- 调用 Signal Gateway。

#### AI Agent Service

- 独立内网服务。
- 统一适配 DeepSeek/Qwen。
- 根据后端提供的上下文生成：
  - Strategy Proposal
  - Strategy Edit Patch
  - Backtest Diagnosis
  - Signal Candidate
- 不保存用户 API key。
- 不调用下单接口。
- 输出必须是结构化 JSON。

#### Market Data Service

- 连接 Hyperliquid WebSocket。
- 同步 market registry。
- 保存/缓存 candles、mark price、funding、OI、volume。
- 对策略运行和回测提供数据。

#### Backtest Service

- 基于 Hyperliquid candle data 做回测。
- 支持 perp long/short、手续费、funding、杠杆、止损止盈、移动止损。
- 输出指标、收益曲线、交易明细、标的归因。

#### Strategy Runtime Worker

- 定时调度启用策略。
- 根据周期在 K 线收盘后运行。
- 构造 AI signal context。
- 调用 AI Agent Service 获取 signal candidate。
- 交给 Risk Validator。

#### Risk Validator

- 强制校验所有 AI 信号。
- 不接受模型突破规则。
- 输出 accept/reject 和原因。

#### Signal Gateway

- 将通过风控的信号交给现有交易后端。
- 支持 HTTP internal API 或 RabbitMQ。
- 负责 idempotency key、重试、dead-letter、事件回写。

#### Existing Trading Backend

- 用户下单配置。
- 用户 API key。
- 真实订单发送。
- 持仓、订单、成交事件。

## 5. 前端页面规划

### 5.1 `/app/ai-trading`

核心页面，第一版优先开发。

布局：

```text
左侧：AI Agent Chat
中间：Strategy Proposal / Backtest / Signal Cards
右侧：Account Risk / Active Strategy / Positions Summary
```

功能：

- 用户用自然语言描述策略。
- AI 生成策略草案。
- 用户修改自然语言约束。
- 用户确认保存策略。
- 用户触发回测。
- 用户启用/暂停策略。

关键组件：

- `AgentChatPanel`
- `AgentMessageList`
- `AgentThinkingTimeline`
- `StrategyProposalCard`
- `StrategyDiffViewer`
- `RiskControlsPanel`
- `BacktestResultCard`
- `SignalPreviewCard`

### 5.2 `/app/markets`

展示可交易标的。

Tabs：

- Crypto Top 20
- Crypto Top 50
- US Stocks Top 20
- US Stocks Top 50
- Indices
- Commodities
- FX

字段：

- Symbol
- DEX
- Category
- Mark Price
- 24h Volume
- Open Interest
- Funding
- Max Leverage
- Tradable
- Risk Tier

操作：

- Ask AI
- Create Strategy
- Add to Universe
- View Market Detail

### 5.3 `/app/strategies/:strategyId`

策略详情。

模块：

- Strategy Spec JSON 可视化。
- 自然语言编辑框。
- 策略版本历史。
- 风控参数。
- 标的池。
- 运行状态。
- 启用/暂停。

### 5.4 `/app/backtests/:backtestId`

回测结果。

模块：

- Equity Curve
- Metrics Grid
- Trade Log
- Symbol Attribution
- Drawdown Chart
- AI Diagnosis
- Enable Strategy CTA

### 5.5 `/app/signals`

实时信号流。

字段：

- Time
- Strategy
- User
- Symbol
- Action
- Confidence
- Risk Status
- Execution Status
- Reason
- Order Event

状态：

- `generated`
- `risk_rejected`
- `accepted`
- `sent_to_backend`
- `order_submitted`
- `partial_filled`
- `filled`
- `rejected`
- `expired`

## 6. 后端 API 规划

### 6.1 Agent Gateway API

```text
POST /api/agent/sessions
POST /api/agent/sessions/:sessionId/messages
GET  /api/agent/sessions/:sessionId/events
POST /api/agent/strategy-proposal
POST /api/agent/strategy-edit
POST /api/agent/backtest-diagnosis
POST /api/agent/signal
```

### 6.2 Strategy API

```text
GET    /api/strategies
POST   /api/strategies
GET    /api/strategies/:strategyId
PATCH  /api/strategies/:strategyId
POST   /api/strategies/:strategyId/enable
POST   /api/strategies/:strategyId/pause
GET    /api/strategies/:strategyId/events
```

### 6.3 Backtest API

```text
POST /api/strategies/:strategyId/backtests
GET  /api/backtests/:backtestId
GET  /api/backtests/:backtestId/events
```

### 6.4 Market API

```text
GET /api/markets
GET /api/markets/:coin
GET /api/markets/:coin/candles
GET /api/markets/:coin/snapshot
```

### 6.5 Signal API

```text
GET  /api/signals
GET  /api/signals/:signalId
POST /api/signals/:signalId/retry
POST /api/signals/:signalId/cancel
```

## 7. 多用户下单配置隔离

### 7.1 分区原则

所有核心数据必须带：

```text
tenant_id
user_id
account_id / account_ref
strategy_id
agent_id
```

下单配置隔离：

```text
user_id
  -> trading_account
    -> strategy_config
      -> runtime_signal
```

AI Agent 只拿约束，不拿密钥。

### 7.2 AI 可见上下文

允许 AI 看到：

```json
{
  "user_id": "u_123",
  "strategy_id": "s_001",
  "allowed_markets": ["BTC", "ETH", "xyz:NVDA"],
  "risk_limits": {
    "max_leverage": 2,
    "max_daily_loss_usd": 100,
    "max_position_notional_usd": 500
  },
  "position_snapshot": {},
  "market_snapshot": {}
}
```

禁止 AI 看到：

- API key
- API secret
- wallet private key
- backend signing credentials
- other users' strategy/memory/signal

### 7.3 Redis Key 规范

共享 Redis 可以用，但 key 必须分区。

```text
market:hyperliquid:core:BTC:snapshot
market:hyperliquid:xyz:NVDA:snapshot
user:{user_id}:strategy:{strategy_id}:state
user:{user_id}:strategy:{strategy_id}:memory
user:{user_id}:strategy:{strategy_id}:signals
user:{user_id}:positions
```

### 7.4 Queue Payload 规范

所有任务必须携带用户范围：

```json
{
  "job_type": "RUN_STRATEGY_TICK",
  "tenant_id": "t_001",
  "user_id": "u_123",
  "strategy_id": "s_001",
  "run_at": "2026-06-08T12:00:00Z"
}
```

## 8. AI 上下文和记忆压缩

### 8.1 上下文分层

每次调用模型只组装必要上下文：

```text
L0 System Rules
L1 User Risk Constraints
L2 Strategy Spec
L3 Compressed Memory
L4 Market Snapshot
L5 Position Snapshot
L6 Recent Events
L7 Current Task
```

不要把完整聊天记录塞给模型。

### 8.2 记忆类型

每个 `user_id + strategy_id` 维护三类 memory：

```text
conversation_summary
strategy_memory
performance_memory
```

示例：

```json
{
  "conversation_summary": "用户偏好低杠杆，只交易 BTC 和大型美股映射标的，不希望频繁交易。",
  "strategy_memory": "当前策略为趋势跟随，5m 入场，1h 过滤，要求止损和日亏损熔断。",
  "performance_memory": "最近三次回测显示 NVDA 胜率较高，SOL 回撤偏大，建议降低 SOL 权重。"
}
```

### 8.3 压缩触发条件

```text
聊天超过 20 条
上下文预计超过 8000 tokens
策略被修改
回测完成
实盘运行日结束
重大执行事件发生
```

### 8.4 压缩保留内容

保留：

- 用户偏好。
- 策略关键决策。
- 风控约束变化。
- 回测结论。
- 失败原因。
- 实盘表现总结。
- 用户明确要求。

丢弃：

- 闲聊。
- 重复解释。
- 过期行情。
- 已废弃策略版本细节。
- 不影响未来决策的中间推理。

### 8.5 AI 调用上下文包

```json
{
  "system_rules": {
    "can_place_orders": false,
    "output_format": "json_only"
  },
  "user_constraints": {},
  "strategy_spec": {},
  "memory_summary": {},
  "market_snapshot": {},
  "position_snapshot": {},
  "recent_events": [],
  "task": "generate_signal"
}
```

## 9. Strategy Spec

所有自然语言策略必须编译成结构化 JSON。

```json
{
  "strategy_id": "s_001",
  "user_id": "u_123",
  "name": "BTC and NVDA Trend Strategy",
  "model_provider": "deepseek",
  "model_name": "deepseek-chat",
  "universe": ["BTC", "xyz:NVDA"],
  "timeframes": ["5m", "15m", "1h"],
  "entry_rules": [
    {
      "type": "trend_filter",
      "timeframe": "1h",
      "condition": "price above ema200 for long"
    }
  ],
  "exit_rules": [
    {
      "type": "stop_loss",
      "required": true
    },
    {
      "type": "take_profit"
    }
  ],
  "risk": {
    "max_leverage": 2,
    "max_position_notional_usd": 500,
    "max_daily_loss_usd": 100,
    "max_trades_per_day": 10,
    "max_open_positions": 3,
    "max_consecutive_losses": 3,
    "require_stop_loss": true
  },
  "status": "draft"
}
```

自然语言修改策略时，AI 输出 patch，不直接覆盖原策略：

```json
{
  "type": "STRATEGY_PATCH",
  "changes": [
    {
      "op": "replace",
      "path": "/risk/max_leverage",
      "value": 2
    }
  ],
  "summary": "将最大杠杆调整为 2x。"
}
```

用户确认后才写入新 strategy version。

## 10. Signal Schema

AI 输出 signal candidate：

```json
{
  "type": "TRADE_SIGNAL",
  "signal_id": "sig_123",
  "user_id": "u_123",
  "strategy_id": "s_001",
  "coin": "BTC",
  "dex": "core",
  "action": "OPEN_LONG",
  "confidence": 0.72,
  "order_type": "market",
  "reduce_only": false,
  "max_notional_usd": 500,
  "stop_loss_px": 98000,
  "take_profit_px": 104000,
  "reason": "1h trend aligned and 5m pullback recovered.",
  "expires_at": "2026-06-08T12:10:00Z"
}
```

无交易机会时必须输出：

```json
{
  "type": "NO_SIGNAL",
  "strategy_id": "s_001",
  "reason": "Setup incomplete or market data stale."
}
```

## 11. 风控校验

后端必须拒绝以下信号：

- 用户未启用策略。
- 标的不在策略 universe。
- 标的不可交易或已下架。
- 信号过期。
- 市场数据过期。
- 缺少止损且策略要求止损。
- 杠杆超过用户/平台限制。
- 单笔 notional 超过限制。
- 日亏损超过限制。
- 今日交易次数超过限制。
- 当前已有冲突持仓。
- 重复信号。
- AI 输出 schema 不合法。

幂等 key：

```text
idempotency_key =
  user_id + strategy_id + coin + action + candle_close_time
```

## 12. Hyperliquid 数据方案

### 12.1 Market Registry

同步：

- Hyperliquid core perp markets。
- HIP-3 builder DEX markets，例如 `xyz`。

字段：

```json
{
  "venue": "hyperliquid",
  "dex": "xyz",
  "coin": "xyz:NVDA",
  "display_symbol": "NVDA",
  "category": "us_stock",
  "asset_id": 110002,
  "max_leverage": 20,
  "size_decimals": 2,
  "mark_price": 0,
  "open_interest": 0,
  "volume_24h": 0,
  "funding": 0,
  "only_isolated": false,
  "is_delisted": false,
  "tradable": true,
  "risk_tier": "watch"
}
```

注意：

- HIP-3 symbol 必须保留 DEX prefix。
- `xyz:NVDA` 和 `NVDA` 不可混用。
- asset id 必须按 Hyperliquid 官方规则计算。

### 12.2 Realtime Data

Market Data Service 订阅：

- `allMids`
- `trades`
- `l2Book`
- `candle`
- `userEvents`
- `orderUpdates`
- `userFills`

REST 兜底：

- `metaAndAssetCtxs`
- `candleSnapshot`
- `clearinghouseState`
- `frontendOpenOrders`
- `userFills`
- `orderStatus`

### 12.3 Staleness Rules

```text
5m 策略：market snapshot 超过 30 秒拒绝信号。
15m 策略：market snapshot 超过 60 秒拒绝信号。
1h 策略：market snapshot 超过 120 秒拒绝信号。
WebSocket 连续失败 N 次，暂停开仓，只允许平仓/不发送新信号。
```

## 13. 回测方案

回测输入：

- Strategy Spec。
- Market universe。
- Start/end time。
- Timeframe。
- Initial capital / notional assumptions。

回测需要支持：

- Long/short。
- Perp leverage。
- Fees。
- Funding。
- Stop loss。
- Take profit。
- Trailing stop。
- Multi-symbol attribution。
- Trade log。

回测输出：

```json
{
  "backtest_id": "bt_123",
  "strategy_id": "s_001",
  "metrics": {
    "total_return": 0.18,
    "max_drawdown": -0.07,
    "sharpe": 1.4,
    "win_rate": 0.54,
    "trade_count": 86
  },
  "equity_curve": [],
  "trades": [],
  "symbol_attribution": [],
  "ai_diagnosis": "策略在 BTC 趋势行情中表现较好，在震荡区间回撤较大。"
}
```

## 14. 与现有下单后端对接

### 14.1 RabbitMQ

从 Lark 文档已知：

- 使用 RabbitMQ 发布/订阅。
- 队列：
  - `QUEUE_STRATEGY_TREND`
  - `QUEUE_STRATEGY_MATRIX`
  - `QUEUE_STRATEGY_GRID`
  - `QUEUE_STRATEGY_LS`
- 消息有效期 10 分钟。
- 直接订阅队列，不要有绑定声明。

建议新增：

```text
QUEUE_AI_TRADING_SIGNAL
```

如果不能新增，则 AI trend strategy 先复用：

```text
QUEUE_STRATEGY_TREND
```

AI signal payload：

```json
{
  "type": "AI_TRADE_SIGNAL",
  "data": {
    "signal_id": "sig_123",
    "user_id": "u_123",
    "strategy_id": "s_001",
    "coin": "BTC",
    "action": "OPEN_LONG",
    "max_notional_usd": 500,
    "stop_loss_px": 98000,
    "take_profit_px": 104000,
    "confidence": 0.72,
    "reason": "Trend continuation setup.",
    "expires_at": "2026-06-08T12:10:00Z",
    "idempotency_key": "..."
  }
}
```

### 14.2 HTTP Internal API

如果使用 HTTP：

```text
POST /internal/trading/signals
```

Headers：

```text
X-Internal-Token
X-Request-Id
```

Body 同 `AI_TRADE_SIGNAL`。

### 14.3 订单事件回传

前端需要展示：

- `ORDER_SUBMITTED`
- `ORDER_FULL_FILLED`
- `ORDER_PARTIAL_FILLED`
- `ORDER_REJECTED`
- `ORDER_CANCELLED`
- `POSITION_OPENED`
- `POSITION_CLOSED`

Lark 文档已看到 `ORDER_FULL_FILLED` 示例，需要补齐其他事件字段。

## 15. 数据库设计

核心表：

```text
ai_agent_sessions
ai_agent_messages
ai_memory_summaries
ai_model_profiles
market_registry
strategy_specs
strategy_versions
backtest_runs
backtest_trades
runtime_signals
risk_decisions
execution_events
agent_runtime_state
```

### 15.1 ai_memory_summaries

```sql
CREATE TABLE ai_memory_summaries (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  strategy_id TEXT,
  memory_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_event_count INTEGER NOT NULL DEFAULT 0,
  token_estimate INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 15.2 strategy_specs

```sql
CREATE TABLE strategy_specs (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  current_version_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 15.3 strategy_versions

```sql
CREATE TABLE strategy_versions (
  id TEXT PRIMARY KEY,
  strategy_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  spec JSONB NOT NULL,
  change_summary TEXT,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 15.4 runtime_signals

```sql
CREATE TABLE runtime_signals (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  strategy_id TEXT NOT NULL,
  coin TEXT NOT NULL,
  dex TEXT NOT NULL,
  action TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  payload JSONB NOT NULL,
  ai_reason TEXT,
  risk_status TEXT NOT NULL,
  risk_reasons JSONB NOT NULL DEFAULT '[]',
  execution_status TEXT NOT NULL DEFAULT 'pending',
  idempotency_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ
);
```

## 16. AI Agent 部署

推荐独立容器：

```text
ai-agent-service
  FastAPI / Python
  DeepSeek adapter
  Qwen adapter
  JSON schema validator
  Prompt templates
  Memory compressor
```

只开放内网：

```text
POST /internal/agent/strategy-proposal
POST /internal/agent/strategy-edit
POST /internal/agent/signal
POST /internal/agent/backtest-diagnosis
POST /internal/agent/compress-memory
```

部署要求：

- 不暴露公网。
- 不保存 API key 明文。
- 不访问 trading secrets。
- 请求必须带内部服务 token。
- 每次请求必须带 `tenant_id`、`user_id`、`strategy_id`。
- 日志中不打印完整 prompt 中的敏感配置。

## 17. Prompt 约束

System Prompt 必须包含：

```text
You are HyperAlpha AI Trading Agent.
You cannot place orders.
You cannot access user API keys.
You can only output JSON that matches the requested schema.
You must obey user risk limits and platform hard limits.
If data is stale or insufficient, output NO_SIGNAL.
You must never trade markets outside allowed_markets.
You must include stop_loss when required.
```

策略生成任务：

```text
Input: user natural language + allowed markets + risk constraints.
Output: STRATEGY_PROPOSAL JSON.
```

信号生成任务：

```text
Input: strategy spec + memory summary + market snapshot + position snapshot + risk state.
Output: TRADE_SIGNAL or NO_SIGNAL JSON.
```

## 18. 安全清单

上线前必须满足：

- AI Agent 无订单权限。
- AI Agent 无用户 API key 权限。
- 每个请求带 `user_id` 和 `strategy_id`。
- DB 查询强制 user scope。
- Redis key 强制 user scope。
- Queue payload 强制 user scope。
- Signal schema validator。
- Risk validator。
- Idempotency key。
- Signal expiry。
- Market data staleness check。
- Execution event audit。
- User pause。
- Strategy pause。
- Global halt。

## 19. 开发排期

### Week 1: Agent 嵌入和策略草案

- AI Trading 页面。
- Agent Gateway。
- DeepSeek/Qwen provider。
- Strategy Proposal JSON。
- Strategy Spec 保存。
- Strategy Edit Patch。

### Week 2: Market 和回测

- Hyperliquid core market registry。
- HIP-3 `xyz` market registry。
- Top 20 / Top 50。
- Candle loader。
- Backtest Service。
- Backtest Result UI。

### Week 3: 实时信号

- Market Data WebSocket Service。
- Strategy Runtime Worker。
- AI Signal Candidate。
- Risk Validator。
- Live Signals UI。

### Week 4: 交易后端对接

- RabbitMQ / HTTP handoff。
- Order event consumer。
- Execution event UI。
- Pause / resume / halt。
- Audit log。

## 20. 需要确认的问题

实现前还需要确认：

1. AI 信号能否使用新队列 `QUEUE_AI_TRADING_SIGNAL`？
2. 如果不能新增队列，AI signal 应该映射到哪一个现有队列？
3. HTTP internal API 的精确字段和状态码是什么？
4. 订单事件除 `ORDER_FULL_FILLED` 外还有哪些类型和字段？
5. 用户在信号 payload 中使用内部 `user_id`、钱包地址，还是两者都传？
6. 平台硬限制默认值是多少？
7. HIP-3 V1 是否只接 `xyz`，还是发现所有 active builder DEX？
8. 回测是否允许用户选择起始资金和手续费模型？

## 21. 第一张开发卡

标题：

```text
Integrate AI Trading Agent into HyperAlpha frontend
```

范围：

```text
Frontend:
- /app/ai-trading
- AgentChatPanel
- StrategyProposalCard
- StrategyDiffViewer

Backend:
- Agent Gateway
- DeepSeek/Qwen call
- Strategy Proposal schema
- Strategy Spec persistence

Safety:
- No order access
- No API key exposure
- user_id + strategy_id scope
- JSON schema validation
```

完成标准：

```text
用户可以在前端用自然语言创建策略。
AI 返回结构化 strategy proposal。
用户可以确认保存。
策略记录绑定 user_id。
AI 服务不接触下单配置。
```

