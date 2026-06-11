# AI Trading Strategy Spec Name Safety Memory

Date: 2026-06-11
Branch: `codex/ai-agent-multitenant-foundation`

## Current

- 本轮继续在 `codex/ai-agent-multitenant-foundation` 本地分支开发；GitHub 上传：按用户要求跳过，不 push、不 merge。
- 本轮目标是补齐 AI Trading strategy spec 展示名安全：用户保存 strategy spec 的 `name` 不能带 API key、token、secret、private key、password、authorization 等敏感文本。
- 新保存的敏感 strategy spec name 走写入前拒绝；历史/脏 `AiTradingStrategySpecRecord.name`、spec list/detail、agent-session context packet 和脏 spec JSON `name` 走响应级脱敏，避免进入 To C UI 或 `Load context`/模型上下文。
- 上一轮 `agent_session_name` 安全边界继续保持：手工 create/update 拒绝 secret-like session name，历史脏 session/spec/event/attempt row 和嵌套 spec/signal JSON 返回 `[redacted_sensitive_session_name]`。
- default production readiness DB-audit blocker 仍保留；真实上线仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。
- 本地验收命令仍以 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 为准；真实交易所执行不属于本地 V1 完成条件。

## Verification Notes

- 新增/更新 route regression 覆盖敏感 strategy spec name 写入前拒绝、legacy polluted strategy record/spec JSON name 不回显、agent-session context packet 中 strategy spec name 脱敏。
- 新增 completion audit status marker：`| AI Trading strategy-spec name safety | Done |`；缺少该 marker 时本地完成度审计会失败。
- 本轮还修复一键本地验收脚本的 macOS `mktemp` portability：临时文件模板改成以 `XXXXXX` 结尾，避免重复运行时生成/碰撞字面量 `.XXXXXX.log` 或 `.XXXXXX.json` 文件；新增 completion-audit 回归覆盖。
- 最新一键本地 V1 验收通过：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` 覆盖 200 条 AI Trading 回归、frontend build、LaunchAgent runtime mirror sync、strict runtime readiness 和 live local mock handoff；runtime readiness 第 7/24 次返回 `ready=true`、`runtime_mirror.current=true`、gateway `mode=http` / `target_kind=local_mock`。
- 最新 live mock handoff 证据：strategy spec `#137`、signal event `#135`、handoff attempt `#133`、gateway response `mock_accepted`、`agent_sessions.total=122`、`handoff_attempts.total=133`、`model_adjustment.ready=false` 且 blocker 为 `model_profile_not_configured`。
- 本地仍不等于实盘上线：GitHub 上传：按用户要求跳过；继续不 push、不 merge。真实上线仍需真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、硬风控生产值、真实 admin 登录态和外部 production evidence。
