# AI Trading Agent Session Name Safety Memory

Date: 2026-06-11
Branch: `codex/ai-agent-multitenant-foundation`

## Current

- 本轮继续在 `codex/ai-agent-multitenant-foundation` 本地分支开发；GitHub 上传：按用户要求跳过，不 push、不 merge。
- 本轮目标是补齐 AI Trading 多会话 Agent 的名称安全：`agent_session_name` 不能把 API key、token、secret、private key、password、authorization 等敏感文本带入 To C UI、response、嵌套 spec/signal JSON 或 DeepSeek/Qwen model-adjust prompt。
- 手工 create/update agent session name 走写入前拒绝；兼容写入、历史脏 row、nested spec/signal JSON 和 model-adjust context 走响应级 `[redacted_sensitive_session_name]` 脱敏。
- `context_summary` 既有边界继续保持：敏感手工摘要写入前拒绝，历史/兼容数据响应前脱敏，runtime budget 只返回 counts-only no summary text。
- default production readiness DB-audit blocker 仍保留；真实上线仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。
- 本地验收命令仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准；真实交易所执行不属于本地 V1 完成条件。

## Verification Notes

- 已新增/更新 route regression，覆盖手工 session name 敏感值拒绝、model-adjust prompt 中敏感 session name 脱敏、legacy polluted session/spec/event/attempt/name/nested JSON 不回显。
- 已新增 completion audit status marker：`| AI Trading agent-session name safety | Done |`；缺少该 marker 时本地完成度审计会失败。
- 后续代码变更后仍需重跑 aggregate regression、frontend build、一键本地 V1 验收、LaunchAgent runtime mirror sync 和 strict runtime mirror check。
