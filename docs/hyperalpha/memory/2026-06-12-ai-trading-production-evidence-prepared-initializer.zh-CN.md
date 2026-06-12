# 2026-06-12 AI Trading Production Evidence Prepared Initializer + API Key Entry Memory

## 本轮新增

- 前端入口修复：
  - `frontend/app/main.tsx` 的 splash 不再等待 account/model/API-key readiness，App shell 先进入。
  - `frontend/app/components/hyper-ai/HyperAiPage.tsx` 右侧配置栏新增固定可见的 `AI Trading Model` / `Configure API key` 入口。
  - 该入口即使 `profile` 或 `aiTradingRuntime` 尚未 ready 也会出现，并打开原有 `LLMConfigModal`。
  - API key 仍只在弹窗 input 中输入，不在 readiness 卡片、运行时卡片、prompt/context 或状态文本中回显。
- `backend/scripts/ai_trading_v1_completion_audit.py` 新增 prepared production evidence 生成路径：
  - CLI: `--prepare-production-evidence-file <repo-external-json>`
  - Optional: `--production-evidence-run-id <safe-run-id>`
  - Optional: `--production-evidence-cutover-window-hours <hours>`
- 该模式会生成仓库外 pending evidence packet，并预填：
  - safe `evidence_run_id`
  - timezone-aware `generated_at` / `expires_at`
  - bounded `cutover_window`
  - safe `cutover_approval_ref`
  - 每个外部验收 item 的 item-specific `artifact_refs` 占位
- 所有 item 仍保持 `status=pending_external_acceptance`，`accepted_count=0`，`production_evidence_ready=false`，`ready_for_live_orders=false`。
- Completion audit 新增 marker：
  - `| AI Trading production evidence prepared initializer | Done |`
  - `| AI Trading frontend main-page API-key config entry | Done |`

## 已验证

- `cd frontend && npm run build` passed.
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "model_api_key_config_entry or model_config_is_nonblocking or model_adjustment_readiness_ui or onboarding_defers_api_key"` returned 4 passing tests.
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "frontend_main_page_api_key_config_entry or frontend_onboarding_api_key_deferral or frontend_model_config_nonblocking_entry or current_repo_completion_audit"` returned 3 passing tests.
- Browser verification on `http://127.0.0.1:8812/#hyper-ai` showed the main page renders without API-key setup and the right panel exposes `AI Trading Model / Configure API key`; clicking it opened the existing Hyper AI Config modal with the API-key field inside the later page.
- `scripts/local-dev/install_launch_agent.sh` synced/restarted the fixed runtime mirror from the current branch.
- `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current` returned `ready=true` after the restart.
- Browser verification on fixed frontend `http://127.0.0.1:5174/app/ai-trading` showed `AI Trading Model / Configure API key` in the main page.
- `cd backend && uv run python -m py_compile scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py` passed.
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "production_evidence_prepared_initializer or production_evidence_prepare_cli or current_repo_completion_audit"` returned 5 passing tests.
- Repo-external CLI smoke with `--prepare-production-evidence-file` returned:
  - `created=true`
  - `production_evidence_root_blockers=[]`
  - `production_evidence_accepted_count=0`
  - `production_evidence_ready=false`
  - explain validation kept `ready_for_live_orders=false`
  - `secret_pattern_count=0`

## 边界

- Branch: `codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 已 push，不 merge。
- Local acceptance command: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`
- Default production readiness DB-audit gate remains blocked.
- default production readiness DB-audit blocker: 未提供真实生产 DB audit / 外部 evidence 前保持阻断。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍需外部生产验收。
- 本轮不触发真实交易所请求、真实模型调用、订单后端 handoff 或 live order 解锁。
- 本轮仍保持 `ready_for_live_orders=false`；真实 macOS reboot、真实 Auth/admin 登录态和真实交易所执行仍是外部 pending。
