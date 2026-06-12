# 2026-06-13 Hyper AI profile 安全记忆

## 本轮目标

- 继续推进 HyperAlpha/Vibe-Trading To C AI Trading Agent 的多用户安全底座。
- 上一轮已收紧 Hyper AI 长期 memory 写入/读取/system prompt 注入边界。
- 本轮补齐 Hyper AI profile 偏好字段边界：用户偏好和 onboarding profile 会进入 system prompt 与 suggestions prompt，不能让 API key、token、Bearer、authorization、private key、password、DB URL 等 secret-like 文本长期保存或进入模型上下文。

## 已完成

- `backend/services/hyper_ai_service.py`
  - 新增 profile 专用 `PROFILE_SENSITIVE_TEXT_PATTERN`、`REDACTED_SENSITIVE_PROFILE_TEXT`、`SENSITIVE_PROFILE_FIELD_ERROR`。
  - 新增 `is_profile_text_sensitive`、`validate_profile_text_for_storage`、`sanitize_profile_text_for_response`。
  - `_build_profile_context` 对 legacy/polluted profile 字段做响应层脱敏后再注入 system prompt。
  - `_save_profile_from_onboarding` 保存 nickname/experience/risk/style 前先验证；secret-like field 会跳过，不落库；日志只记录 presence，不记录原始 nickname/experience。
  - `get_suggestions_context` 返回脱敏后的 profile fields。
  - `build_suggestions_prompt` 再次清洗 profile fields，避免未来调用方绕过 `get_suggestions_context`。
- `backend/api/hyper_ai_routes.py`
  - `/api/hyper-ai/profile` 返回脱敏 profile preference fields。
  - `/api/hyper-ai/profile/preferences` 写入前验证 trading_style/risk_preference/experience_level/preferred_symbols/preferred_timeframe/capital_scale；secret-like field 返回固定 400 `profile_field_rejected_sensitive`，不回显原文。
- `backend/tests/test_hyper_ai_profile_safety.py`
  - 新增 profile preferences secret-like write rejection regression。
  - 新增 legacy polluted profile read/system prompt/suggestions prompt redaction regression。
  - 新增 onboarding parsed profile secret-like field skip regression。
- `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`
  - backend compile 和 AI Trading backend regression test list 纳入 `tests/test_hyper_ai_profile_safety.py`。
- `backend/scripts/ai_trading_v1_completion_audit.py`
  - aggregate runner required phrases 纳入 `tests/test_hyper_ai_profile_safety.py`。
  - completion audit 新增 `AI Trading Hyper AI profile safety` required marker。
- `backend/tests/test_ai_trading_v1_completion_audit.py`
  - minimal repo fixture 和 missing-marker regression 覆盖新 marker。
- `docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md`
  - 新增 Done marker 和 focused verification。
- `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md`
  - 更新 focused profile safety 证据。

## 验证

- `cd backend && uv run python -m py_compile api/hyper_ai_routes.py services/hyper_ai_service.py tests/test_hyper_ai_profile_safety.py`：通过。
- `cd backend && uv run pytest tests/test_hyper_ai_profile_safety.py -q`：4 passed。
- `cd backend && uv run pytest tests/test_hyper_ai_profile_safety.py tests/test_ai_trading_v1_completion_audit.py -q -k "hyper_ai_profile_safety or current_repo_completion_audit"`：6 passed, 158 deselected。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local`：通过，`local_v1_accepted=true`、`ready_for_live_orders=false`、current branch `codex/ai-agent-multitenant-foundation`、无 local blockers、production evidence 仍 pending。

## 未改变

- 没有启用真实订单后端 handoff。
- 没有调用真实 DeepSeek/Qwen API。
- 没有改变 signal-only/no-direct-order/backtest gate/user confirmation/hard-risk 边界。
- 没有改变 LLM API key 存储模型；真实 API key 仍只应通过 Hyper AI profile 的 encrypted key 字段保存，不应放入 profile preference/memory/context。
- 没有合并分支。

## 分支与验收边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮提交后继续只 push 到该 feature branch。
- 已 push，不 merge；不要合并到主分支，除非用户明确验收并要求合并。
- 本地 V1 完成度仍以 strict-local completion audit 和一键本地 acceptance runner 为准；完整一键命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- Production live readiness 仍必须保留 default production readiness DB-audit blocker，直到外部真实 Auth/JWKS、订单后端、DeepSeek/Qwen profile/API key 和生产审批 evidence 完整通过。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收；真实交易所执行继续不属于本地 V1。
