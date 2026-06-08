# HyperAlpha AI Trading 开发治理与交付流程

版本：v0.1  
日期：2026-06-08  
范围：AI Trading Agent、策略生成、回测、信号、风控、前端集成、后端对接。

## 1. 目的

本文件定义开发前置规则：

- 先做上下文记忆压缩，再开发。
- 前端、后端、策略、AI Agent 的职责边界清楚。
- 每个功能必须审核、测试、验收。
- 测试未通过不能验收。
- 未验收不能标记完成。
- GitHub 上传必须走分支管理，不直接合并。

## 2. 开发前置动作

每次开始一个功能前必须完成：

1. 读取最新压缩记忆：

```text
docs/hyperalpha/memory/latest
```

如果没有 `latest` 指针，则读取最新日期的 memory 文件。

2. 读取产品/开发主文档：

```text
docs/hyperalpha/full-development-plan.zh-CN.md
```

3. 更新任务状态文档：

```text
docs/hyperalpha/status/{feature-name}.status.md
```

4. 创建功能分支。

5. 明确本功能的：

- scope
- out of scope
- affected modules
- test plan
- acceptance criteria
- rollback plan

## 3. 压缩记忆管理

### 3.1 记忆文件位置

```text
docs/hyperalpha/memory/
```

命名：

```text
YYYY-MM-DD-context-summary.zh-CN.md
YYYY-MM-DD-feature-{feature-name}-summary.zh-CN.md
```

### 3.2 latest 指针

建议新增：

```text
docs/hyperalpha/memory/latest.md
```

内容只链接最新压缩记忆：

```md
# Latest Memory

- Current: 2026-06-08-context-summary.zh-CN.md
```

### 3.3 何时压缩

必须压缩：

- 开发一个新功能前。
- 完成一个功能后。
- 测试失败并发生设计变更后。
- 验收前。
- 合并/关闭分支前。

### 3.4 压缩内容

保留：

- 用户确认的需求。
- 安全边界。
- API/schema 决策。
- 风控规则。
- 数据隔离规则。
- 测试结果。
- 已知风险。
- 未验收事项。

丢弃：

- 无关聊天。
- 过时实现细节。
- 已废弃方案。
- 中间推理。

## 4. 功能状态管理

每个功能必须有状态文件。

路径：

```text
docs/hyperalpha/status/{feature-name}.status.md
```

模板：

```md
# Feature Status: {feature-name}

Status: planned | in_progress | implemented | test_failed | test_passed | review_requested | accepted | blocked

Branch:
Owner:
Reviewer:
Created:
Updated:

## Scope

## Out Of Scope

## Implementation Notes

## Test Plan

## Test Results

## Acceptance Criteria

## Acceptance Result

## Open Issues

## Rollback Plan
```

状态含义：

- `planned`: 只规划，未开发。
- `in_progress`: 正在开发。
- `implemented`: 已完成代码，但未测试。
- `test_failed`: 测试失败，不能验收。
- `test_passed`: 测试通过，可进入审核。
- `review_requested`: 等待审核。
- `accepted`: 已验收，可标记完成。
- `blocked`: 被外部信息或依赖阻塞。

强制规则：

```text
implemented != done
test_passed != accepted
accepted 才能进入完成清单
```

## 5. 分支管理

### 5.1 分支命名

所有开发分支使用：

```text
codex/{type}-{short-name}
```

类型：

- `docs`
- `frontend`
- `backend`
- `agent`
- `market-data`
- `backtest`
- `risk`
- `signal`
- `integration`

示例：

```text
codex/docs-development-governance
codex/frontend-ai-trading-shell
codex/backend-agent-gateway
codex/agent-memory-compression
codex/signal-risk-validator
```

### 5.2 禁止事项

- 不直接在 `main` 开发。
- 不把多个大功能混进一个分支。
- 不自动合并到 `main`。
- 不在测试失败时创建 ready PR。
- 不在未验收时标记功能完成。

### 5.3 GitHub 上传规则

每个功能上传后保持独立分支：

```text
git push -u origin codex/{type}-{short-name}
```

PR 默认状态：

```text
Draft PR
```

只有满足以下条件才可改为 Ready：

- 所有测试通过。
- 自审完成。
- 风险说明已写。
- 验收清单已准备。
- 没有阻塞项。

## 6. 开发门禁

每个功能走以下流程：

```text
1. Plan
2. Context Compression
3. Branch
4. Implement
5. Self Review
6. Test
7. Fix
8. Test Pass
9. Review Package
10. Acceptance
11. Push Branch
12. Keep Unmerged
```

### 6.1 Plan

输出：

- scope
- affected files
- data/security impact
- test plan
- acceptance criteria

### 6.2 Implement

要求：

- 小步提交。
- 保持边界清晰。
- 不改无关模块。
- 不碰用户密钥。
- 不引入 AI 直接下单路径。

### 6.3 Self Review

自审清单：

- 是否跨用户泄露数据？
- 是否暴露 API key？
- 是否绕过风控？
- 是否新增未受控下单路径？
- 是否保留审计日志？
- 是否有幂等？
- 是否有失败状态？

### 6.4 Test

至少包含：

- unit tests
- integration tests
- schema validation tests
- authorization / tenant isolation tests
- risk validator tests
- frontend smoke tests

涉及交易信号必须额外测试：

- expired signal rejected
- duplicate signal rejected
- over-limit signal rejected
- missing stop-loss rejected
- stale market data rejected
- unauthorized market rejected

### 6.5 Acceptance

验收必须在测试通过后。

验收材料：

- 功能说明。
- 测试结果。
- 已知风险。
- 截图或 API 示例。
- 未完成事项。
- 回滚方式。

## 7. 前端/后端/策略协调规则

### 7.1 前端

前端只能：

- 发起对话。
- 展示策略。
- 展示回测。
- 展示信号。
- 展示执行状态。
- 启用/暂停策略。

前端不能：

- 保存 API key。
- 直接调用 DeepSeek/Qwen。
- 直接调用 Hyperliquid。
- 直接发送订单。

### 7.2 后端

后端负责：

- 鉴权。
- user/tenant scope。
- 组装 AI 上下文。
- 保存 strategy spec。
- 风控。
- 审计。
- signal handoff。

### 7.3 AI Agent

AI Agent 只能：

- strategy proposal。
- strategy patch。
- backtest diagnosis。
- signal candidate。
- memory compression。

AI Agent 不能：

- 读用户 API key。
- 下单。
- 修改账号配置。
- 跨用户访问 memory。

### 7.4 策略运行服务

策略运行服务负责：

- 按周期读取行情。
- 构造 signal context。
- 调用 AI Agent。
- 接收 signal candidate。
- 交给风控。

不负责：

- 真实下单。
- 绕过风控。

## 8. 测试矩阵

### 8.1 AI Agent

- Strategy proposal schema。
- Strategy patch schema。
- Signal schema。
- NO_SIGNAL schema。
- Prompt injection 防护。
- User scope 不泄露。
- Memory compression 保留关键约束。

### 8.2 Backend

- Auth required。
- tenant/user isolation。
- strategy CRUD。
- backtest trigger。
- signal validation。
- risk rejection。
- idempotency。
- audit logging。

### 8.3 Frontend

- AI Trading 页面可打开。
- Chat message 发送成功。
- Strategy proposal card 展示。
- Strategy diff 可确认/取消。
- Backtest result 可展示。
- Live signal 状态可展示。
- Pause button 生效。

### 8.4 Integration

- Agent Gateway -> AI Agent。
- Backend -> Backtest Service。
- Runtime -> AI Signal。
- Risk -> Signal Gateway。
- Signal Gateway -> Trading Backend mock。
- Order event -> frontend。

## 9. 验收门槛

不能验收：

- 测试失败。
- 没有测试记录。
- 没有状态文件。
- 没有 scope/out-of-scope。
- 没有 rollback plan。
- 信号能绕过风控。
- AI 能接触密钥。
- 前端能直接下单。
- 未记录 open issues。

可以验收：

- 测试全部通过。
- 自审完成。
- 审核材料完整。
- 风险可接受。
- 未完成事项已标记。

## 10. 第一批开发分支建议

### Branch 1

```text
codex/docs-development-governance
```

内容：

- 本文件。
- 初始压缩记忆。
- 状态模板。

### Branch 2

```text
codex/backend-agent-gateway
```

内容：

- Agent Gateway API。
- DeepSeek/Qwen internal call。
- Strategy proposal schema。
- User scope enforcement。

### Branch 3

```text
codex/frontend-ai-trading-shell
```

内容：

- `/app/ai-trading` 页面骨架。
- AgentChatPanel。
- StrategyProposalCard。
- SSE/streaming 状态。

### Branch 4

```text
codex/agent-memory-compression
```

内容：

- memory summary table/API。
- compression prompt。
- context pack builder。

### Branch 5

```text
codex/market-hyperliquid-registry
```

内容：

- Hyperliquid core markets。
- HIP-3 xyz markets。
- Top 20/50。
- market registry API。

### Branch 6

```text
codex/signal-risk-validator
```

内容：

- signal schema。
- risk validator。
- idempotency。
- rejection reasons。

## 11. 当前执行建议

在正式开发功能前，先提交本治理文档和初始压缩记忆。

然后第一张开发卡应该是：

```text
codex/backend-agent-gateway
```

原因：

- 后端边界先明确。
- 前端不直接碰 AI/下单。
- 后续页面、回测、信号都通过 Gateway 接入。

