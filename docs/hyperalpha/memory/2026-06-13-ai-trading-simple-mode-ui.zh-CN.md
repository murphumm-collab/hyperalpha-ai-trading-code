# HyperAlpha 开发记忆压缩：AI Trading 页面减法 / 简洁模式

## 本轮目标

- 回应“页面内容太多，用户用不明白”的产品问题。
- 不删除原有 AI Trading 能力，把默认入口从全量运维/审计面板改成 To C 用户能直接使用的简洁流程。

## 变更

- `frontend/app/components/hyper-ai/HyperAiPage.tsx`
  - 新增默认开启的 `aiTradingSimpleMode`。
  - AI Trading 默认只显示：
    - 高流动性标的选择：优先 `BTC`、`ETH`、`HYPE`、`SOL`、`xyz:NVDA`、`xyz:TSLA`、`xyz:AAPL`、`xyz:AMD`，再补市场 universe 前 8 个。
    - 自然语言交易目标输入。
    - 固定安全摘要：最大亏损 `1%`、杠杆 `3x`、只出信号。
    - `问 AI` 和单一主按钮。
  - 单一主按钮按状态流转：
    - 无策略：生成策略。
    - 有未保存草案：保存策略。
    - 已保存未确认：确认策略。
    - 已确认但无 handoff-ready 回测：要求勾选历史回测确认后跑回测。
    - 回测就绪：生成信号。
  - 原有 Gateway、Model、Sessions、Specs、Signals、Attempts、Agent session、市场分组、策略/回测/信号历史全部保留，但默认收进 `高级详情`。
  - 窄屏下标的按钮从 4 列改为 3 列，避免 `xyz:NVDA` / `xyz:TSLA` 被截断。
- `frontend/app/locales/en.json` / `frontend/app/locales/zh.json`
  - 新增简洁模式中英文文案。
- `backend/tests/test_ai_trading_frontend_readiness_source.py`
  - 新增源码守卫：AI Trading 默认简洁模式存在，高级详情默认隐藏，简洁主按钮/目标输入存在。

## 验证

- `backend/.venv/bin/pytest backend/tests/test_ai_trading_frontend_readiness_source.py -q`：39 passed。
- `cd frontend && npm run build`：通过，仅剩既有 Browserslist / dynamic-import / chunk-size warnings。
- `scripts/local-dev/install_launch_agent.sh`：已同步 runtime mirror 并重启 `5174/8802/5621` 本地服务。
- 浏览器自检：
  - `http://127.0.0.1:5174/app/ai-trading` 默认显示 `AI Trading 简洁模式`。
  - 默认按钮包含 `BTC`、`ETH`、`HYPE`、`SOL`、`xyz:NVDA`、`xyz:TSLA`、`xyz:AMD`、`ZEC`、`问 AI`、`生成策略`。
  - `data-testid="ai-trading-advanced-details"` class 为 `hidden`，高级内容默认不可见。
  - 点击 `高级详情` 后原 Gateway/Agent session/market universe/历史记录内容可展开。
  - 390px 宽度下按钮无 `scrollWidth > clientWidth` 溢出。

## 产品边界

- 本轮只做前端减法和流程收敛，不改真实订单后端、不解锁 live orders。
- 无 DeepSeek/Qwen API key 时仍可进入页面、选标的、填写目标、看到模型稍后配置状态；真实 AI 生成/模型调整仍需要用户配置模型。
- 高级审计能力保留给测试、运营和后续验收，不作为 To C 默认入口。
