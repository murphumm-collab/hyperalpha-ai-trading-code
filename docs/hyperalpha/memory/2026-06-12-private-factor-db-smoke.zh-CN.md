# HyperAlpha 开发记忆：Private Factor DB Smoke

日期：2026-06-12

当前分支：`codex/ai-agent-multitenant-foundation`

GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；已 push，不 merge。

## 本轮完成

- 新增 `backend/scripts/ai_trading_private_factor_precompute_smoke.py`，用于本地 Postgres DB 级验证 private custom factor precompute writer-reader。
- smoke 使用隔离 exchange `codex_smoke`、symbol `CXSFACTOR` 和唯一 `pfsmoke_*` 前缀，创建 Alice/Bob 两个用户，给两人创建同名私有 factor 但不同 `custom_factor_id`。
- smoke 写入 2000 根最近 1h 合成 K 线，固定 `FactorEffectivenessService` 的 symbol universe 到合成 symbol，避免触发真实交易所或 watchlist 数据。
- smoke 分别调用 `compute_single_factor` 与 `query_factors`，证明：
  - Alice/Bob 各 1 条 `user_factor_values` latest value。
  - Alice/Bob 各 216 条 `user_factor_effectiveness` IC/ICIR rows。
  - `query_factors` detail/history/ranking 走 user-scoped reader。
  - shared `factor_values` / `factor_effectiveness` 对该私有 factor 保持 0 rows。
  - smoke finally cleanup 清理 users/custom_factors/klines/user_factor/shared-factor 相关测试数据。

## 验证结果

- `DATABASE_URL=postgresql://alpha_user:alpha_pass@127.0.0.1:5432/alpha_arena uv run python scripts/ai_trading_private_factor_precompute_smoke.py --pretty` 通过，返回 `success=true`。
- 清理验证对 `crypto_klines`、`custom_factors`、`users`、`user_factor_values`、`user_factor_effectiveness`、`factor_values`、`factor_effectiveness` 的 smoke prefix/exchange/symbol 查询全部为 0。

## 边界

- 此 smoke 不调用模型、不调用交易所、不调用订单后端、不解锁 live orders。
- default production readiness DB-audit blocker 仍保持阻断，真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部验收。
- 聚合本地验收入口仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`，完成后必须继续只推送 feature branch。
