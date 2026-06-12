# 2026-06-13 Hyper AI Custom Endpoint SSRF Guard

## 目标

继续在 `codex/ai-agent-multitenant-foundation` 上做本地 V1 安全收口，不合并分支，不打开实盘下单。本轮目标是收紧 Hyper AI custom LLM endpoint：防止 To C 用户/API 把后端拿去探测 localhost、私网、link-local、reserved IP、HTTP public endpoint、query/fragment 或 malformed URL。

## 已完成

- `validate_llm_base_url_for_storage` 现在对 custom provider base URL 执行固定错误码校验：
  - `llm_base_url_invalid`
  - `llm_base_url_https_required`
  - `llm_base_url_local_or_private_rejected`
  - `llm_base_url_query_or_fragment_rejected`
  - `llm_base_url_rejected_sensitive`
- `/api/hyper-ai/test-connection` 和 `/api/hyper-ai/profile/llm` 会在任何网络连接测试或 profile 保存前拒绝不安全 custom endpoint，不回显原始 URL、host、query、fragment 或解析异常。
- 旧 DB 中的 legacy custom private endpoint 会在 `/api/hyper-ai/profile` 中显示 `[redacted_sensitive_llm_base_url]`，`get_llm_config` 返回 `configured=false`、`base_url_blocked=true` 和固定 `base_url_blocked_reason`，不会继续调用污染 endpoint。
- 本地开发保留显式开关：`HYPER_AI_ALLOW_PRIVATE_LLM_BASE_URL=true` 时允许 local/private HTTP endpoint，默认关闭。
- preset provider override guard、model readiness sensitive endpoint gate、custom sensitive URL redaction 继续保留。

## 验证

- Passed: `cd backend && uv run python -m py_compile api/hyper_ai_routes.py services/hyper_ai_service.py tests/test_hyper_ai_llm_base_url_safety.py`
- Passed: `cd backend && uv run pytest tests/test_hyper_ai_llm_base_url_safety.py -q` returned 16 passing tests.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_frontend_readiness_source.py -q -k "model_adjustment_readiness or runtime_reports_model_adjustment_readiness_without_secrets or model_adjustment_uses_profile_model"` returned 3 passing tests.

## 仍不改变

- 真实 DeepSeek/Qwen API key live model-adjust 仍未验收。
- 真实 HyperAlpha 订单后端 URL/token handoff 仍未验收。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍属于外部验收。
- Full local acceptance command remains `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`; default production readiness DB-audit blocker 继续作为非实盘 gate。
- `ready_for_live_orders` 必须继续保持 `false`。

## 分支边界

- 当前分支：`codex/ai-agent-multitenant-foundation`
- 远程目标：`origin/codex/ai-agent-multitenant-foundation`
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation
- 已 push，不 merge
- 不合并，不直接切到生产实盘。
