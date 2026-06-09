# 2026-06-10 AI Trading Admin Handoff Audit Readiness Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：Admin-only AI Trading production readiness 现在包含非敏感 handoff attempt audit warning/counts。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- Backend readiness service：
  - 新增 `build_handoff_attempt_audit_report(db)`，从 `AiTradingSignalHandoffAttemptRecord` 统计全局 handoff attempt 结果。
  - Admin readiness component 新增 `handoff_audit`。
  - `handoff_audit` 返回 `total`、`by_result`、`gateway_ready`、`gateway_not_ready`、`latest_non_submitted`、`secret_values_returned=false`。
  - 存在 failed attempt 时 warning `handoff_attempt_failed_present`。
  - 存在 blocked attempt 时 warning `handoff_attempt_blocked_present`。
  - `latest_non_submitted` 只返回 attempt/spec/signal IDs、symbol、action、result、gateway_ready，不返回 user IDs、gateway URL、token、authorization、raw error body 或 downstream response body。

- Admin API：
  - `/api/ai-trading/admin/production-readiness` 注入 DB session，并把 handoff audit report 合并进共享 production readiness report。
  - CLI production readiness checker 保持 env-only、no-network、no-submit，不读取 DB。

- 文档：
  - Status doc 标记为 `Local V1 Admin Handoff Attempt Audit Readiness Gate Complete / Remote Push Skipped`。
  - V1 checklist 更新到最新本地验收数字：59 regressions、spec `#35`、signal event `#33`、`agent_sessions.total=20`、`handoff_attempts.total=31`。

## 已验证

- `cd backend && uv run python -m py_compile services/ai_trading_production_readiness_service.py api/ai_trading_routes.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_production_readiness_check.py`
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py -q`：8 passed，覆盖 admin-only `handoff_audit` failed/blocked warnings 和 attempt secret redaction。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：59 passed，4 个既有 UTC deprecation warnings。
- `scripts/local-dev/install_launch_agent.sh`：passed；第一次 strict env check 命中 backend 冷启动，重试后 ready。
- `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict`：`ready=true`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；最新 live mock handoff 证据为 spec `#35`、signal event `#33`、gateway response `mock_accepted`、`agent_sessions.total=20`、`handoff_attempts.total=31`。

## 下一步注意

- 继续开发时不要把 `handoff_audit` 下放到普通用户 runtime；普通 runtime 继续只看 current-user 非敏感 handoff attempt summary。
- 真实生产验收仍需要真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen 用户 profile、真实 logged-in admin UI，以及真实交易所执行验收。
