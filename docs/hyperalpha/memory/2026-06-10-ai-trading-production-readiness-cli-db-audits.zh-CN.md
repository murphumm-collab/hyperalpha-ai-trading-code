# 2026-06-10 AI Trading Production Readiness CLI DB Audits Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading production readiness CLI 现在支持显式 `--include-db-audits`，用于命令行生产验收时加入持久化 handoff attempt 与 agent-session context audit。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- `backend/scripts/ai_trading_v1_production_readiness_check.py`：
  - 新增 `--include-db-audits`。
  - 默认行为不变：仍是 no-network/no-submit env readiness gate，不打开 DB。
  - 显式开启 DB audits 时：
    - 读取 `build_handoff_attempt_audit_report(db)`。
    - 读取 `build_agent_session_context_audit_report(db)`。
    - 注入同一个 `build_report(...)` readiness component 标准。
  - DB audit 不可用时 fail closed：
    - 增加 blocker `db_audit:db_audit_unavailable`。
    - 只返回 `error_type` 和 `secret_values_returned=false`。
    - 不返回 DATABASE_URL、数据库密码、异常原文或连接串。

- `backend/tests/test_ai_trading_production_readiness_check.py`：
  - 新增 DB audit 成功路径测试：
    - 构造 failed handoff attempt 与 over-budget agent session。
    - 断言 CLI report 包含 `handoff_audit` warning 和 `agent_session_context` blocker。
    - 断言不会泄漏 fake authorization/token 或 long summary 原文。
  - 新增 DB audit 不可用 fail-closed 测试：
    - session factory 抛出包含 fake password 的异常。
    - report 只返回 `RuntimeError` 类型，不返回 `password=` 或 fake password。

## 已验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_production_readiness_check.py tests/test_ai_trading_production_readiness_check.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_production_readiness_check.py -q`：6 passed。
- `cd backend && env -u AUTH_REQUIRE_VERIFIED_BEARER -u AUTH_JWKS_URL -u AUTH_JWT_ISSUER -u AUTH_JWT_AUDIENCE -u AUTH_JWT_ALGORITHMS -u AUTH_ADMIN_USERNAMES -u AI_TRADING_SIGNAL_GATEWAY_ENABLED -u AI_TRADING_SIGNAL_GATEWAY_URL -u AI_TRADING_SIGNAL_GATEWAY_TOKEN -u AI_TRADING_PRODUCTION_HANDOFF_APPROVED -u AI_HARD_MAX_ORDER_NOTIONAL_USD -u AI_HARD_REQUIRE_STOP_LOSS -u AI_HARD_REQUIRE_TAKE_PROFIT uv run python scripts/ai_trading_v1_production_readiness_check.py --strict`：按预期 exit 1，默认 production readiness 仍被真实 Auth/JWKS、生产 handoff、硬风控 blockers 拒绝。
- `cd backend && uv run python scripts/ai_trading_v1_production_readiness_check.py --strict --include-db-audits`：按预期 exit 1；当前 shell 默认 DB config 不能连接 audit DB，report 追加 `db_audit:db_audit_unavailable`，只返回 `error_type=OperationalError`，不返回 DB URL/password/exception text。
- `cd backend && DATABASE_URL=<local Postgres alpha_arena URL> uv run python scripts/ai_trading_v1_production_readiness_check.py --include-db-audits`：DB audit 读取成功，返回：
  - `handoff_audit.total=35`
  - `agent_session_context.total=25`
  - `agent_session_context.over_budget_count=0`
  - `agent_session_context.redacted_context_summary_count=1`
  - 仍因真实 Auth/JWKS、生产 handoff、硬风控未配置而 `production_ready=false`
  - 输出不包含 DB URL/password、gateway token 或 summary 原文。
- `cd backend && uv run pytest tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：63 passed，5 个既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh` 已纳入 default production readiness DB-audit blocker gate：在 frontend/runtime/mock handoff 之前显式运行 `ai_trading_v1_production_readiness_check.py --strict --include-db-audits` 并要求 exit 1。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：passed。
- 单独运行 aggregate runner 使用的 DB-audit expected-failure 命令：按预期 exit 1，返回 auth/signal_handoff/hard_risk/db_audit blockers，未输出数据库 URL、凭据或异常原文。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed，覆盖 backend compile、63 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、默认 production handoff blocker、默认 production readiness blocker、默认 production readiness DB-audit blocker、frontend build、runtime readiness 和 live local mock handoff；最新证据为 strategy spec `#41`、signal event `#39`、agent sessions `26`、handoff attempts `37`、gateway response `mock_accepted`、model-adjust blocker `model_profile_not_configured`。

## 下一步注意

- 本切片只增强 production readiness CLI 的可验证范围，不改变交易 API、模型调用、handoff 或订单执行。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key、真实登录态 admin visual acceptance、实际 macOS reboot 仍未验收。
- AI Trading 仍保持 signal-only；真实订单执行仍必须由订单后端处理。
