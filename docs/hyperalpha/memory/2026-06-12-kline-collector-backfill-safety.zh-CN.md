# 2026-06-12 K-line Collector / Backfill Safety Memory

## 本轮新增

- Hyperliquid K-line collector 增加统一 payload normalization，兼容 CCXT `timestamp/open/high/low/close/volume` 和 Hyperliquid native `t/o/h/l/c/v` candle 字段。
- 当前 K-line 采集现在使用返回数组的最后一根 candle，避免把历史数组第一根误当最新行情。
- malformed candle payload 会被跳过或返回 `None`，日志只记录固定上下文，不把原始 payload、API key-like 文本、上游响应或 URL 回显到 To C UI。
- K-line backfill 后台任务失败时只持久化固定 `K-line backfill failed`，状态 API 对 legacy/raw `error_message` 也只返回同一固定标签。
- `/api/klines/backfill` 校验 period 与 symbol；active-task 冲突不再回显旧任务 symbol；unsupported exchange 返回固定 `Unsupported exchange`。
- 一键本地验收 runner 和 completion audit 现在要求 `tests/test_kline_collectors.py` 与 `| AI Trading K-line collector/backfill safety | Done |` marker。

## 已验证

- `cd backend && uv run python -m py_compile api/kline_routes.py services/kline_collectors.py services/kline_backfill_manager.py tests/test_kline_routes.py tests/test_kline_collectors.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`
- `cd backend && uv run pytest tests/test_kline_collectors.py tests/test_kline_routes.py -q`
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "kline_collector_and_backfill_safety or kline_collector_safety_gate or current_repo_completion_audit"`

## 边界

- Branch: `codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。
- Local acceptance command: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`
- Default production readiness DB-audit gate remains blocked.
- default production readiness DB-audit blocker: 未提供真实生产 DB audit / 外部 evidence 前保持阻断。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部生产验收。
- 本轮不触发真实交易所请求、模型调用、订单后端 handoff 或 live order 解锁。
- 本轮仍保持 `ready_for_live_orders=false`；真实 DeepSeek/Qwen、真实订单后端、真实 Auth/JWKS、真实 macOS reboot 和生产登录态验收仍是外部 pending。
- GitHub 已同步时继续只推送 `codex/ai-agent-multitenant-foundation` 分支，不 merge。
