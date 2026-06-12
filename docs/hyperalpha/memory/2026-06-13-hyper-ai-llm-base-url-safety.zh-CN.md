# 2026-06-13 Hyper AI LLM base URL 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 上一轮已收紧 suggested questions 输出边界。
- 本轮补齐 Hyper AI LLM 配置 URL 边界：用户配置自定义 DeepSeek/Qwen/custom LLM 时，`base_url` 不能携带 API key、token、Bearer、private key、password、DB URL、`sk-*` key 或 URL userinfo；历史污染的 custom base URL 也不能从 `/profile` 泄漏或被内部模型调用使用。

## 已完成

- `backend/services/hyper_ai_service.py`
  - 新增 `REDACTED_SENSITIVE_LLM_BASE_URL`、`SENSITIVE_LLM_BASE_URL_ERROR`。
  - 新增 `is_llm_base_url_sensitive`、`validate_llm_base_url_for_storage`、`sanitize_llm_base_url_for_response`。
  - `save_llm_config` 写入前验证 base URL，secret-like/userinfo URL 会 fail closed。
  - `get_llm_config` 对 legacy polluted custom `llm_base_url` 返回 `configured=false`、`base_url_blocked=true` 和固定 redaction，不再调用污染 endpoint。
  - 非 custom provider 如存在污染 override，会忽略该 override 并回落 provider preset base URL。
- `backend/api/hyper_ai_routes.py`
  - `/api/hyper-ai/profile` 返回 `llm_base_url` 前做安全投影。
  - `/api/hyper-ai/profile/llm` 在 test/save 前验证 `base_url`；污染 URL 返回固定 400 `llm_base_url_rejected_sensitive`，不触发网络连接测试，不回显原文。
  - `/api/hyper-ai/test-connection` 同样在网络调用前拒绝污染 `base_url`。
- `backend/tests/test_hyper_ai_llm_base_url_safety.py`
  - 新增 profile LLM save path 污染 URL 拒绝且不打网络 regression。
  - 新增 test-connection path 污染 URL 拒绝且不打网络 regression。
  - 新增 legacy polluted custom base URL 在 `/profile` 脱敏且 `get_llm_config` blocked regression。
  - 新增 valid base URL storage/response preservation regression。
  - 新增 source guard 防止旧式 raw assignment / raw request base URL pass-through 回归。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 和 AI Trading backend regression test list 纳入 `tests/test_hyper_ai_llm_base_url_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - aggregate runner required phrases 纳入 `tests/test_hyper_ai_llm_base_url_safety.py`。
  - completion audit 新增 `AI Trading Hyper AI LLM base URL safety` required marker。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 和 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker 和 focused verification。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 focused LLM base URL safety 证据。

## 验证

- `cd backend && uv run python -m py_compile api/hyper_ai_routes.py services/hyper_ai_service.py tests/test_hyper_ai_llm_base_url_safety.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py -q`：5 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_llm_base_url_safety or current_repo_completion_audit"`：7 passed, 161 deselected。
- `bash -n scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`：通过。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、current branch `codex/ai-agent-multitenant-foundation`、无 local blockers、production evidence 仍 pending。

## 未改变

- 没有启用真实订单后端 handoff。
- 没有调用真实 DeepSeek/Qwen API。
- 没有改变 API key 加密存储模型；本轮只处理 LLM config base URL。
- 没有改变 signal-only/no-direct-order/backtest gate/user confirmation/hard-risk 边界。
- 没有合并分支。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮提交后继续只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 完成度仍以 strict-local completion audit 和一键本地 acceptance runner 为准；完整一键命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen profile/API key 和生产审批 evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。
