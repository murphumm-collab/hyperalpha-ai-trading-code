# HyperAlpha 开发记忆压缩：页面自检 + 安全空态

## 本轮目标

- 回答并补做“有没有打开页面全部自检一次”：实际打开本地固定 runtime 页面做浏览器 smoke，而不是只跑后端测试。
- 修复自检时发现的页面级 500/无限 loading 问题，保持 AI Trading 页面可进入、API key 后置配置、无白屏、无 console error/warn。

## 变更

- `backend/api/arena_routes.py`
  - `/api/arena/trades` 在 testnet/mainnet 分支读取 snapshot DB 时，如果 `hyperliquid_trades` 表缺失或 snapshot DB 不可用，不再抛 500。
  - 返回安全空 feed：`accounts=[]`、`trades=[]`，并只写固定 warning，不记录原始 SQL/provider/secret-like 异常。
- `backend/api/market_data_routes.py`
  - `/api/market/kline-with-indicators/{symbol}` 拉取 K 线/指标失败时返回安全空 series：`count=0`、`klines=[]`、`indicators={}`。
  - 不再把 provider error、API key、token、private key 等异常文本拼进 HTTP detail。
- `frontend/app/components/klines/KlinesView.tsx`
  - 新增 `marketDataLoading` 状态。
  - 市场数据卡片在无 watchlist、价格接口失败或返回空数据时显示空态，不再永久显示 `加载中...`。
- `frontend/app/locales/en.json` / `frontend/app/locales/zh.json`
  - 新增 `kline.noMarketData` / `暂无市场数据`。
- 新增 focused tests：
  - `backend/tests/test_arena_routes.py`
  - `backend/tests/test_market_data_routes.py`

## 浏览器自检结果

- 服务：LaunchAgent runtime mirror 已同步并重启，`5174` frontend、`8802` backend、`5621` mock gateway 均监听。
- `http://127.0.0.1:5174/app/ai-trading`
  - 进入页面不需要 DeepSeek/Qwen API key。
  - 页面内显示 `配置 API key`，点击后打开后置 Hyper AI config modal，`稍后配置` 可关闭。
  - 冷启动后稳定显示 Gateway available、Local mock/http、Model profile missing、Sessions/Specs/Signals/Attempts、BTC/HYPE/`xyz:NVDA` market universe。
- `/#comprehensive`
  - Dashboard 正常渲染；snapshot trade 表缺失时显示空交易记录，不再 console 500。
- `/#klines`
  - K-Line 页面正常渲染；行情为空时显示 `暂无市场数据` 和 `No K-line data available`，不再无限 loader，不再后端 500。
- `/#settings`
  - Settings shell 正常渲染并加载 watchlist symbols。
  - 本地未登录/auth-disabled 下 admin production readiness controls 隐藏仍是预期；真实 admin 可视验收仍待外部 Auth/admin 登录态。
- `/app/ai-trading/sessions/ait%3Abtc%3A3e52b9e47e7f`
  - Session detail 正常显示 status、symbols、specs、signals、handoff attempts、summary chars。
- `/app/ai-trading/backtests/172`
  - 当前本地 DB 没有 attached Program Backtest evidence，页面显示安全 no-evidence 空态，不白屏。
- 最终干净浏览器 tab：只统计打开之后的 console `error/warn`，结果为 0。

## 验证

- `cd backend && uv run python -m py_compile api/arena_routes.py api/market_data_routes.py tests/test_arena_routes.py tests/test_market_data_routes.py`
- `cd backend && uv run pytest tests/test_arena_routes.py tests/test_market_data_routes.py -q`：2 passed。
- `cd frontend && npm run build`：通过，仅剩既有 baseline-browser-mapping / Browserslist / dynamic-import / chunk-size warnings。
- `scripts/local-dev/install_launch_agent.sh`：已同步 runtime mirror 并重启本地服务。
- `cd backend && uv run python scripts/ai_trading_v1_env_check.py --strict`：`ready=true`。
- `curl http://127.0.0.1:8802/api/arena/trades?limit=20&trading_mode=testnet`：200，空 feed。
- `curl http://127.0.0.1:8802/api/market/kline-with-indicators/BTC?market=hyperliquid&period=1m&count=500`：200，空 K-line series。

## 治理边界

- 当前开发分支：`codex/ai-agent-multitenant-foundation`。
- GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation；本轮修改完成后仍只允许 push 到该远程 feature branch。
- 已 push，不 merge；没有合并主分支或 production 分支。
- 本地 V1 总验收命令仍是 `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff`。
- 本地 V1 完成边界必须继续包含 default production readiness DB-audit blocker，真实生产 handoff/readiness 在未提供外部证据前保持阻断。

## 仍未验收

- 真实 Program Backtest evidence detail 页面需要有真实 attached evidence 的 spec 再做可视验收；当前只验证 no-evidence 安全空态。
- 真实 admin 登录态 Settings Admin AI Trading Production Readiness 可视验收仍待 Auth/JWKS/admin session。
- 真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key 仍未验收。
- 真实生产 handoff、真实交易所执行和 production live-order acceptance 仍未验收。
