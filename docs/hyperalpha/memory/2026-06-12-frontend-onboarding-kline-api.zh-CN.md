# HyperAlpha AI Trading 开发记忆压缩：Onboarding 白屏兜底 + K-line local DB API

日期：2026-06-12
分支：`codex/ai-agent-multitenant-foundation`

## 当前结论

- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation。
- 本轮仍然只在 `codex/ai-agent-multitenant-foundation` 开发；已 push，不 merge。
- 生产实盘仍未解锁：completion audit 保持 `ready_for_live_orders=false`，外部验收仍要求真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
- default production readiness DB-audit blocker 必须继续保持，直到真实生产 evidence 和显式 live-ready confirmation 完成。

## 本轮新增

- 修复 Hyper AI onboarding 跳过/API key 后白屏风险：根渲染由 `AppErrorBoundary` 包裹，子组件 render 崩溃时显示固定恢复页和 reload 按钮，不再整页空白，也不把 raw exception 文本渲染给用户。
- 修复 `ContactDialog` 与 Radix `TooltipTrigger asChild` 嵌套产生的 ref warning：`ContactDialog` 现在使用 `React.forwardRef` 并把 trigger props/ref 下放到真实 trigger button。
- `/api/klines/data` 从占位响应改为只读本地 `CryptoKline` 查询：按当前用户 exchange preference 或显式 `exchange` 读取，支持 period/window/limit/environment，symbol/period/window 输入 fail closed，错误响应使用固定 label，不调用外部交易所或订单服务。
- 一键本地验收 runner 已纳入 `api/kline_routes.py` compile 与 `tests/test_kline_routes.py` regression；completion audit 要求 runner 和 status 文档保留 K-line gate。

## 已验证

- `cd frontend && npm run build` 通过，仅剩既有 baseline-browser-mapping/Browserslist/dynamic-import/chunk-size warning。
- `cd backend && uv run python -m py_compile api/kline_routes.py tests/test_kline_routes.py scripts/ai_trading_v1_completion_audit.py tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py` 通过。
- `cd backend && uv run pytest tests/test_kline_routes.py -q` 返回 3 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_frontend_readiness_source.py -q -k "onboarding_uses_safe_model_and_stream_errors or root_app_has_error_boundary or contact_dialog_forwards_trigger_ref"` 返回 3 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py -q -k "current_repo_completion_audit or kline_local_db_api or kline_routes_regression_gate or frontend_onboarding_blank_page_guard"` 返回 4 passing tests。
- `cd backend && uv run pytest tests/test_ai_trading_v1_completion_audit.py tests/test_ai_trading_frontend_readiness_source.py tests/test_kline_routes.py -q -k "current_repo_completion_audit or kline_data or kline_local_db_api or kline_routes_regression_gate or root_app_has_error_boundary or contact_dialog_forwards_trigger_ref or frontend_onboarding_blank_page_guard"` 返回 9 passing tests。
- `cd backend && uv run python scripts/ai_trading_v1_completion_audit.py --strict-local` 通过：`local_v1_accepted=true`、`ready_for_live_orders=false`、`github_upload=pushed_to_origin`、`git_governance.status=accepted`。
- `scripts/local-dev/install_launch_agent.sh` 已同步 runtime；`cd backend && AI_TRADING_RUNTIME_READINESS_ATTEMPTS=60 AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS=5 uv run python scripts/ai_trading_v1_env_check.py --strict --require-runtime-mirror-current` 返回 `ready=true`、`runtime_mirror.current=true`、runtime `mode=http`、`target_kind=local_mock`。
- in-app Browser 验证：打开 `http://127.0.0.1:5174/#ai-trading`，点击 `跳过` 后 Hyper AI 主界面正常渲染，未显示恢复 fallback，时间过滤后的最近 console error/warn 为空。

## 继续开发注意

- 运行完整本地验收仍使用：`scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 真实上线前仍必须补：真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key。
- 不要把 AI Trading agent 改成直接下单；当前边界仍是 signal-only，订单发送由后端订单服务处理。
