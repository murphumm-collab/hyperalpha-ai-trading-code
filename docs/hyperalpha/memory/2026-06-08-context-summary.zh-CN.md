# HyperAlpha AI Trading 压缩上下文记忆

版本：v0.1  
日期：2026-06-08  
用途：作为开发前的压缩记忆基线，后续开发、审核、测试、验收都以此为上下文起点。

## 1. 产品目标

在 `app.hyperalpha.org` 现有平台中加入 AI Trading Agent：

- 用户通过自然语言创建和调整策略。
- 系统使用 Hyperliquid 数据做回测。
- AI 生成策略方案、约束条件、回测诊断和结构化交易信号。
- 前端负责展示、确认、暂停和监控。
- 后端负责用户隔离、风控、审计和信号转发。
- 现有交易后端仍然是唯一真实下单入口。

## 2. 已确认边界

- 账号系统已有，不在本阶段开发范围内。
- 用户下单配置/API key 管理已有，不在 AI Agent 中处理。
- 真实下单后端已有，AI 不直接下单。
- 第一版使用 DeepSeek 或 Qwen。
- 第一版使用 Hyperliquid 数据。
- 第一版直接支持实盘，但必须由后端风控和用户额度控制。
- 第一版标的为交易量最大的 crypto 和 HIP-3 美股/指数标的 Top 20 / Top 50。

## 3. 安全原则

```text
AI 不直接下单。
AI 不读取 API key / secret / private key。
AI 不跨用户读取上下文。
AI 不跨策略读取 memory。
AI 只输出 strategy proposal、strategy patch、backtest diagnosis、signal candidate。
所有 signal 必须经过 schema 校验和后端风控。
没有测试不能验收。
没有验收不能标记完成。
```

## 4. 服务分工

```text
Frontend
  展示、编辑、确认、暂停、监控。

API Backend
  鉴权、用户隔离、策略保存、上下文组装、风控、审计、信号转发。

AI Agent Service
  DeepSeek/Qwen 调用、策略生成、策略编辑、信号候选、记忆压缩。

Market Data Service
  Hyperliquid REST/WebSocket、行情缓存、K线、OI、funding。

Backtest Service
  基于 Hyperliquid 数据跑回测。

Strategy Runtime Worker
  定时运行启用策略，生成信号候选。

Trading Backend
  现有真实下单系统。
```

## 5. 前端 MVP 页面

- `/app/ai-trading`
- `/app/markets`
- `/app/strategies/:strategyId`
- `/app/backtests/:backtestId`
- `/app/signals`

## 6. 多用户隔离规则

所有数据必须绑定：

```text
tenant_id
user_id
account_id / account_ref
strategy_id
agent_id
signal_id
```

Redis key 必须分区：

```text
user:{user_id}:strategy:{strategy_id}:state
user:{user_id}:strategy:{strategy_id}:memory
user:{user_id}:strategy:{strategy_id}:signals
```

Queue payload 必须带：

```text
tenant_id
user_id
strategy_id
idempotency_key
```

## 7. 上下文与记忆压缩

每次 AI 调用只使用压缩上下文：

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

Memory 类型：

- `conversation_summary`
- `strategy_memory`
- `performance_memory`
- `risk_memory`
- `execution_memory`

压缩触发：

- 聊天超过 20 条。
- 预计上下文超过 8000 tokens。
- 策略被修改。
- 回测完成。
- 实盘运行日结束。
- 重大执行事件发生。

## 8. 开发流程记忆

每个功能必须走：

```text
Plan
  -> Implement
  -> Self Review
  -> Tests
  -> Fix until tests pass
  -> Acceptance Package
  -> User/Owner Acceptance
  -> Mark Done
  -> Push Branch
```

规则：

- 测试未通过：不能验收。
- 未验收：不能标记完成。
- 做到哪里必须在状态文档中标记。
- 每个功能独立分支。
- 不直接合并到 main。
- GitHub 上传后保持分支，不自动 merge。

## 9. 当前已确认与待确认

已确认：

- GitHub 完整代码仓库：`https://github.com/murphumm-collab/hyperalpha-ai-trading-code`
- 工作分支：`codex/hyperalpha-product-plan`
- 早先创建的 `hyperalpha-ai-trading` 是空的私有占位仓库；完整代码同步以 `hyperalpha-ai-trading-code` fork 仓库为准。
- 终端 `git push` 仍需要 GitHub CLI/浏览器 sudo 二次验证；当前远程同步通过 GitHub Web/Connector 提交完成。

仍待确认：

- 是否允许新增 RabbitMQ 队列 `QUEUE_AI_TRADING_SIGNAL`。
- HTTP internal API 精确字段。
- 订单事件完整类型和字段。
- 平台默认硬风控参数。
- HIP-3 V1 只接 `xyz` 还是发现全部 active builder DEX。
