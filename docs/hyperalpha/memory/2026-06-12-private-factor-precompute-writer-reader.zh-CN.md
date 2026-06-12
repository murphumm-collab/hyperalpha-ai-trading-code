# HyperAlpha 开发记忆：Private Factor Precompute Writer-Reader

日期：2026-06-12

当前分支：`codex/ai-agent-multitenant-foundation`

GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；已 push，不 merge。

## 本轮完成

- GitHub 同步已打通并保持远端 feature branch，不合并。
- 私有自定义 factor 的 schema 已从上一轮的 `user_factor_values` / `user_factor_effectiveness` 继续推进到 writer-reader 闭环。
- Hyper AI `compute_factor` 对当前用户私有 custom factor 不再写共享 `factor_values` / `factor_effectiveness`，而是按 `user_id + custom_factor_id` 写入：
  - `user_factor_values`
  - `user_factor_effectiveness`
- Hyper AI `query_factors` 在指定 `factor_name + symbol` 时可从 user-scoped 表读取 private factor 最新值、effectiveness 和 history。
- Hyper AI `query_factors` 在只指定 `symbol` 做 factor ranking 时，会把当前用户已经预计算的 private factor 结果并入排名，并标记 `source=user_private`。
- `factor_resolver` 和 `compute_single_factor` 的 public builtin expression 查询边界已收窄为当前用户私有 factor 或 `user_id IS NULL` 的平台公共 builtin expression，避免同名/同 source 的跨用户串读。

## 安全边界

- 公共 builtin / public custom expression factor 继续使用共享全局表。
- 用户私有 custom factor 结果按 `user_id + custom_factor_id` 隔离，不以 `factor_name` 作为跨用户共享身份。
- 此变更只生成 factor value/effectiveness 数据，不改变 signal-only/no-order 边界，也不启用实盘订单。

## 验收状态

- 新增 completion audit marker：`| AI Trading private factor precompute writer-reader | Done |`
- 新增 source guard：检查 private writer、reader、resolver user/public boundary、status marker。
- 生产真实 DeepSeek/Qwen、真实 Auth/JWKS、真实订单后端、真实交易所执行仍是外部验收，不因本轮完成而解锁 live orders。
- default production readiness DB-audit blocker 仍保持阻断，真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部验收。
- 聚合本地验收入口仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`，完成后必须继续只推送 feature branch。
