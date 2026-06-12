# 2026-06-12 K-line Maintenance Endpoint Safety Memory

## 本轮新增

- K-line maintenance endpoints 继续收紧安全错误输出：
  - `DELETE /api/klines/backfill-tasks/{task_id}` 内部失败只返回 `Failed to delete task`。
  - `GET /api/klines/gaps/{symbol}` 校验 symbol、限制 `days` 为 1-30，并且内部失败只返回 `Failed to detect gaps`。
  - `GET /api/klines/supported-symbols` 内部失败只返回 `Failed to get supported symbols`。
- 这些端点不再把 raw exception、订单后端 URL、token/API key-like 文本、legacy task symbol 或上游响应拼进 To C API response。
- Completion audit 新增 `| AI Trading K-line maintenance endpoint safety | Done |` gate，防止状态文档漏记这条边界。

## 已验证

- `cd backend && uv run pytest tests/test_kline_routes.py -q -k "delete_backfill_task_uses_fixed_error_label or detect_gaps_validates_symbol_and_uses_fixed_error_label or supported_symbols_uses_fixed_error_label"`
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "kline_maintenance_endpoint_safety or current_repo_completion_audit"`
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`

## 边界

- Branch: `codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。
- Local acceptance command: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`
- Default production readiness DB-audit gate remains blocked.
- default production readiness DB-audit blocker: 未提供真实生产 DB audit / 外部 evidence 前保持阻断。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部生产验收。
- 本轮不触发真实交易所请求、模型调用、订单后端 handoff 或 live order 解锁。
- 本轮仍保持 `ready_for_live_orders=false`；真实 macOS reboot、真实 Auth/admin 登录态和真实交易所执行仍是外部 pending。
