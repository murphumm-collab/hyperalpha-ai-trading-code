# 2026-06-10 AI Trading Agent Context Limit UI Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading agent-session detail 页现在展示 context limit metadata。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- Frontend：
  - `/app/ai-trading/sessions/{agent_session_id}` detail 页新增只读 `Context limits` 面板。
  - 面板展示 Specs / Signals / Attempts 的 `returned / requested / max`。
  - 面板展示 `Summary max chars` 和 `redacted, no credentials`。
  - 不触发模型调用、handoff 或订单后端，只读取已有 current-user session context packet。

- 本地 runtime：
  - 重新运行 `scripts/local-dev/install_launch_agent.sh` 同步 runtime mirror。
  - Strict env check 返回 `ready=true`。

## 已验证

- `cd frontend && npm run build`：passed；剩余为既有 browser-baseline/Browserslist/chunk-size warnings。
- `scripts/local-dev/install_launch_agent.sh`：passed。
- `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict`：`ready=true`，runtime totals 为 strategy specs `35`、signal events `33`、agent sessions `20`、handoff attempts `31`。
- In-app Browser：打开 `http://127.0.0.1:5174/app/ai-trading/sessions/ait%3Abtc%3A4d53a40f6789`，跳过本地 onboarding，不输入 API key；确认 `Agent session detail`、`Context limits`、`returned / requested / max`、`Summary max chars`、`2000`、`redacted, no credentials` 渲染，无 visible error。

## 下一步注意

- 本地 visual smoke 使用 auth-disabled dev stack；真实 logged-in admin/user acceptance 仍需要真实 Auth/JWKS。
- Context limit UI 是只读可观测性，不改变执行边界；AI 仍不能直接下单。
