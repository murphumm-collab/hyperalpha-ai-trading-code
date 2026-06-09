# 2026-06-10 AI Trading Production Evidence Gate Memory

## 当前状态

- 分支：`codex/ai-agent-multitenant-foundation`
- 本地切片：AI Trading V1 completion audit 现在支持生产外部验收 evidence 文件校验，用来把真实 Auth/JWKS、真实订单后端、真实模型 profile、管理员可视化、生产 session detail、实际 reboot、真实交易所执行等七项外部验收记录成脱敏 JSON。
- GitHub 上传：按用户要求跳过；只做本地开发、测试、验收标记和本地 commit。

## 已完成

- `backend/scripts/ai_trading_v1_completion_audit.py`：
  - 继续支持 `--strict-local`，要求本地 V1 证据完整，包括 aggregate local acceptance runner、default production readiness DB-audit blocker、signal-only gateway contract、development governance 和 latest compressed memory。
  - `--strict-local` 现在还要求一键本地验收 runner 包含 production evidence template expected-failure gate。
  - 新增 `--production-evidence-file`，读取 `hyperalpha.ai_trading.external_acceptance.v1` evidence JSON。
  - Evidence 必须覆盖七个外部验收项，且每项都为 `status=accepted`、有 `validated_at`、`validated_by`、`evidence_summary`、`artifact_refs`、`secret_values_returned=false`。
  - Evidence 会扫描 Authorization/Bearer、API key/password/private key/access token、DB URL、OpenAI-style `sk-...`、AWS-style key 等常见密钥模式。
  - 即使 evidence 完整，默认仍保持 `ready_for_live_orders=false`；必须显式追加 `--allow-live-ready-from-evidence` 才允许 live-ready 变 true。
  - 继承最新一键本地验收证据：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。

- `docs/hyperalpha/ai-trading-v1-production-evidence.template.json`：
  - 提供七项外部验收的脱敏 evidence 模板。
  - 模板自身全是 pending，不能通过 `--strict-production`。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：
  - 新增 `Production evidence template remains blocked` expected-failure 步骤，显式运行 completion audit 的 `--production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production`。

- `backend/tests/test_ai_trading_v1_completion_audit.py`：
  - 从 3 条扩展到 5 条。
  - 覆盖 accepted sanitized production evidence 仍需显式 live-ready confirmation。
  - 覆盖 missing evidence item 不能 live ready。
  - 覆盖 Authorization/Bearer secret-pattern 不能 live ready。

## 已验证

- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：passed。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q`：5 passed。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：passed，返回 `local_v1_accepted=true`、`ready_for_live_orders=false`、`production_evidence.provided=false`、`production_track=pending_external_acceptance`。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production`：按预期 exit 1，返回 `production_evidence.provided=true`、`production_evidence.ready=false`、`accepted_count=0`、`required_count=7`、`ready_for_live_orders=false`。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_env_check.py tests/test_ai_trading_live_stack_acceptance.py tests/test_ai_trading_model_adjust_live_acceptance.py tests/test_ai_trading_production_readiness_check.py tests/test_ai_trading_production_readiness_api.py tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q`：68 passed，5 个既有 UTC deprecation warnings。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`：passed；一键本地验收覆盖 backend compile、68 条 AI Trading 回归、API smoke、live model-adjust 默认阻断、默认 production handoff/readiness/DB-audit blockers、local V1 completion boundary audit、production completion boundary expected blocker、production evidence template expected blocker、frontend build、runtime readiness 和 live local mock handoff。最新证据为 strategy spec `#44`、signal event `#42`、agent sessions `29`、handoff attempts `40`、gateway response `mock_accepted`、model-adjust blocker `model_profile_not_configured`。

## 下一步注意

- 本切片只增加生产验收 evidence 校验，不改变交易 API、模型调用、handoff 或订单执行。
- 本地 V1 accepted 不等于 production ready；真实 evidence 未完成时 `ready_for_live_orders=false` 是正确状态。
- Evidence 文件不能包含 API keys、bearer tokens、DB URLs、private keys、raw Authorization headers 或用户 secret。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍必须在外部环境完成验收后写入脱敏 evidence。
- AI Trading 仍保持 signal-only；真实订单执行仍必须由 HyperAlpha 订单后端处理。
