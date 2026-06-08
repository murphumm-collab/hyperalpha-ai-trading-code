# AI Agent Multi-Tenant Foundation Status

Date: 2026-06-08
Branch: `codex/ai-agent-multitenant-foundation`

## Current Status

Status: Local Checkpoint Complete / Remote Push Blocked

Local checkpoint: current branch `HEAD`

## Scope

- User-scoped Hyper AI profile, memory, conversations, skills, and tool settings.
- User-scoped Signal AI chat/history plus account ownership validation.
- User-scoped Prompt AI, Program AI, and Attribution AI chat/history entry points.
- User-scoped Program CRUD, bindings, preview-run, executions, and backtest result reads.
- User-scoped Kline AI analysis creation, history, and detail reads.
- User-scoped K-line data service exchange resolution and backfill task visibility/deletion.
- User-scoped account dashboard/config/action routes and asset curve reads.
- User-scoped Binance wallet/config/manual-action routes and per-user quota/premium checks.
- User-scoped Arena trades, model chat, position, analytics, PnL status reads, and PnL update action.
- User-scoped PromptTemplate, SignalDefinition, and SignalPool ownership.
- User-scoped Hyper Insight wallet-tracking runtime config, token sync, websocket state, and wallet-signal callbacks.
- Hyper AI destructive tools validate current-user ownership before calling shared delete services.
- AI stream polling tasks are owner-scoped so users can only poll, inspect, or confirm their own background AI tasks.
- AI stream polling tasks and chunks are persisted to the database for single-server restart recovery.
- Context compression memory extraction stores long-term memories under the current user.
- User-scoped Hyperliquid/Binance symbol watchlists, with shared data collectors reading the aggregate symbol union.
- User-scoped exchange preference selection so one user's Hyperliquid/Binance/Aster choice does not overwrite another user's UI state.
- Hyperliquid account, wallet, manual order, action summary, and wallet upgrade APIs validate current-user account ownership.
- Hyperliquid execution environment defaults to account-level settings for setup, switching, AI decisions, Program Trader, and trading commands.
- Trading command AI prompts use each account owner's watchlist instead of a cross-user aggregate list.
- Automated AI Trader and Program Trader order execution pass a shared hard risk validator before exchange order placement.
- Auth-aware Hyper AI, Signal AI, Prompt AI, Program AI, Attribution AI, Program Trader, Program Backtest, Kline AI, Prompt Manager, and Signal Manager frontend requests.
- Auth-aware Attribution analytics and Trade Replay frontend requests.
- Auth-aware trading account, strategy, wallet, asset-curve, Arena model-chat, and action-log frontend requests.
- Auth-aware identity runtime token, membership sync, Signal Manager strategy-analysis, market-regime config, factor analysis, and premium sampling-config requests.
- Auth-aware frontend watchlist reads for Klines, Arena NewsZone, Signal Manager, and Dashboard Insight.
- User-scoped membership sync and logout clearing so one user cannot overwrite or delete other users' premium status.
- Development progress and acceptance markers.
- Manual order-placement APIs are not changed in this slice.

## Progress Markers

| Item | Status | Evidence |
| --- | --- | --- |
| Dedicated branch created | Done | `codex/ai-agent-multitenant-foundation` |
| Development spec saved | Done | `.omc/autopilot/spec.md` |
| Implementation plan saved | Done | `.omc/plans/autopilot-impl.md` |
| Backend Python runtime bound | Done | `backend/pyproject.toml` and `backend/uv.lock` constrain backend runtime to Python `>=3.12,<3.14` so `llvmlite==0.44.0` resolves with wheels |
| Backend user resolver | Done | `backend/api/auth_utils.py` |
| Bearer JWT/JWKS verification | Done | `AUTH_JWKS_URL` enables RS256/384/512 signature verification; `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE`, `AUTH_JWT_ALGORITHMS`, and `AUTH_REQUIRE_VERIFIED_BEARER` tighten production auth |
| Hyper AI DB user scoping | Done | `add_hyper_ai_user_scope.py`, model `user_id` fields |
| Hyper AI route filtering | Done | Profile, conversations, memory, skills, tools scoped by current user |
| Signal AI route filtering | Done | Chat/history endpoints use current user; `accountId` is ownership-checked |
| Prompt AI route filtering | Done | Chat/history endpoints use current user; `accountId` is ownership-checked |
| Program AI route filtering | Done | Chat/history endpoints use current user; Program CRUD/bindings/backtest reads are scoped |
| Attribution AI route filtering | Done | Chat/history endpoints use current user; `accountId` is ownership-checked |
| Kline AI route filtering | Done | Analysis creation validates account owner; history/detail use current user |
| K-line data/backfill user scoping | Done | K-line data routes resolve exchange from current user or explicit `exchange`; backfill tasks store `user_id` and are listed/statused/deleted by owner |
| Account route ownership | Done | Account list/overview/strategy/create/update/delete, LLM test, manual AI trigger, builder checks, disable-trading, dashboard visibility, and asset curve reads are scoped to current user |
| Binance route ownership | Done | Binance wallet setup/config/list/delete, balance, positions, manual order, close-position, summary, stats, limited binding, daily quota, and rebate checks are current-user guarded |
| Arena route ownership | Done | Arena trades, model-chat, model-chat snapshots, positions, analytics, PnL sync status, and PnL update action filter by current-user accounts |
| Strategy entity ownership | Done | `add_strategy_entity_user_scope.py`; PromptTemplate, SignalDefinition, SignalPool CRUD scoped by current user |
| Hyper Insight runtime user scoping | Done | `add_hyper_insight_wallet_runtime_user_scope.py`; token/status/websocket state and wallet pool matching are user-scoped |
| AI tool user propagation | Done | Hyper AI tool execution passes `user_id` into subagents, wallet status, tracked wallet tools, Strategy Radar, `save_program`, `create_ai_trader`, and `web_search` config lookup |
| AI delete tool ownership guard | Done | Trader, prompt, signal, pool, program, and binding delete tools validate current-user ownership before deletion |
| AI stream task ownership | Done | Stream tasks store `user_id`; poll/status/confirmation endpoints enforce current-user access |
| AI stream task persistence | Done | `add_ai_stream_persistence.py`; stream tasks/chunks are persisted and stale running tasks hydrate as interrupted after restart |
| Compression memory ownership | Done | `compress_messages(..., user_id=...)` propagates current user into background memory extraction |
| Symbol watchlist ownership | Done | `add_user_symbol_watchlists.py`; Hyperliquid/Binance watchlists are stored per user, with aggregate reads for collectors |
| Watchlist API/AI tool scoping | Done | `/symbols/watchlist` GET/PUT and Hyper AI `get_watchlist/update_watchlist` pass current `user_id` |
| Exchange preference ownership | Done | `/api/users/exchange-config` reads/writes `UserExchangeConfig` by resolved request user; frontend `ExchangeContext` uses `authFetch` |
| Trading command watchlist isolation | Done | Hyperliquid/Binance AI prompts use each account owner's watchlist while price collectors use the union |
| Hyperliquid API ownership guard | Done | Account-level Hyperliquid config, balance, positions, manual order, wallet, agent wallet, actions summary, and upgrade-check APIs validate current user |
| Hyperliquid account execution environment | Done | Setup/switch/client defaults, AI decision logs, Program Trader, and trading commands use account-level environment before global fallback |
| Automated execution hard risk guard | Done | `hard_risk_service.py`; AI Trader and Program Trader reject orders exceeding hard leverage, single-trade margin, projected margin usage, optional TP/SL, or TP/SL side rules |
| Frontend token propagation | Done | `authFetch`/auth-aware `apiRequest` used by Hyper AI, onboarding, Signal AI, Prompt AI, Program AI, Attribution AI chat, Program Trader, Program Backtest, Kline AI, Prompt Manager, Signal Manager, and polling |
| Frontend attribution analytics auth | Done | Attribution summary/dimension/trade list/account list plus Trade Replay kline/replay/chat-stream requests use `authFetch` |
| Frontend trading account auth | Done | Binance wallet setup/status/balance/quota/delete, account strategy, asset curve, Arena model-chat, account deletion, and Hyperliquid action logs use `authFetch` |
| Frontend identity/signal config auth | Done | Auth runtime token sync, membership sync/clear, Signal Manager analysis/config, Market Regime config, factor evaluation, and premium sampling config use `authFetch` |
| Frontend watchlist auth | Done | Klines, Arena NewsZone, Signal Manager, and Dashboard Insight use auth-aware watchlist fetches |
| Membership sync isolation | Done | `/api/users/sync-membership` and `/api/users/clear-membership` update/delete only the current request user's `UserSubscription` |
| Backend checks | Passed | `python3 -m py_compile` on changed backend files |
| Frontend checks | Passed | `corepack pnpm -C frontend build` |
| Local commit | Done | Current branch `HEAD` |
| Remote push | Blocked | Terminal GitHub HTTPS credentials unavailable |
| Acceptance | Partial | Multi-user AI foundation and automated hard-risk checks passed; live Casdoor env acceptance, distributed job queue, and real exchange execution remain unaccepted |

## Verification Log

- Passed: Python syntax compile for changed backend files.
- Passed: Auth utility syntax compile after configurable JWKS verification implementation.
- Passed: `uv run` backend environment now resolves with Python 3.13.13 after constraining backend Python to `>=3.12,<3.14`.
- Passed: Auth helper smoke test in `uv run`: unverified local decode works for demo mode; `AUTH_REQUIRE_VERIFIED_BEARER=true` rejects Bearer tokens when JWKS is not configured.
- Passed: Frontend production build with Vite.
- Passed: Static search found no remaining `user_id=1`, bare `get_llm_config(db)`, or default-user AI entry in the scoped AI files except removed legacy helper before cleanup.
- Passed: Static search found no remaining bare `fetch(` in Program Trader, Program Backtest, or Program AI chat components.
- Passed: Kline AI route compile and frontend build after Kline auth/scoping changes.
- Passed: Prompt/Signal ownership route compile and frontend build after strategy entity `user_id` migration and auth-aware manager requests.
- Passed: Hyper Insight wallet runtime route/service compile and frontend build after per-user token/status/websocket scoping.
- Passed: Hyper AI delete tool ownership guard compile and whitespace check.
- Passed: AI stream owner scoping route/service compile, whitespace check, and frontend production build.
- Passed: AI stream persistence models/migration/service syntax compile.
- Passed: Compression memory owner propagation compile, static call-site search, and whitespace check.
- Passed: User symbol watchlist route/service/tool compile and static search confirming user-facing GET/PUT and Hyper AI tools pass `user_id`.
- Passed: Trading command static review confirming account AI prompt symbols are sourced from each account owner's watchlist.
- Passed: Frontend watchlist fetch audit found no remaining bare `/symbols/watchlist` requests; production Vite build passed.
- Passed: Hyperliquid owner guard route compile, whitespace check, and frontend production build after wallet selector auth update.
- Passed: Hyperliquid account execution environment compile and whitespace check.
- Passed: Hard risk service smoke test in `uv run`: accepted normal small entry, rejected oversized/overleveraged/invalid TP-SL entry, allowed close while margin usage was high.
- Passed: AI Trader and Program Trader hard risk integration compile in both system Python and `uv run` backend environment.
- Passed: Exchange preference isolation smoke test in `uv run`: two users saved different exchanges and read back independent values.
- Passed: `python3 -m py_compile backend/api/user_routes.py` after exchange-config scoping.
- Passed: Frontend production build after `ExchangeContext` switched to `authFetch`.
- Passed: K-line exchange/task isolation smoke test in `uv run`: two users resolved different exchanges; one user's backfill task was invisible to the other user.
- Passed: K-line service/routes/model/migration syntax compile in both system Python and `uv run` backend environment.
- Passed: Static search found no remaining `UserExchangeConfig.user_id == 1` reads in backend API/services.
- Passed: Account route ownership smoke test in `uv run`: account list, cross-user disable/trigger rejection, dashboard visibility filtering, and paper asset curve user filtering passed.
- Passed: Account route and asset curve syntax compile in both system Python and `uv run` backend environment.
- Passed: Static account route scan confirmed account queries now use `current_user` or `_ensure_account_owner`.
- Passed: Binance route ownership smoke test in `uv run`: wallet list user filtering, cross-user config/delete/quota rejection, and per-user premium check passed.
- Passed: Binance route syntax compile in both system Python and `uv run` backend environment.
- Passed: Arena read route smoke test in `uv run`: paper trades, model chat, snapshots, positions, and analytics returned only the current user's account data.
- Passed: Arena update-PnL empty-user smoke test in `uv run`: user with no accounts returns an empty success result and does not scan exchange wallets.
- Passed: Arena route syntax compile in both system Python and `uv run` backend environment.
- Passed: Static search found no remaining bare `fetch(` in Attribution Analysis or Trade Replay analytics components; frontend production build passed.
- Passed: Static search found no remaining bare `fetch(` in Binance wallet, exchange wallet panel, Strategy Panel, Arena asset view, Hyperliquid asset chart, Prompt Backtest, Settings account deletion, or System Logs components; frontend production build passed.
- Passed: AuthContext, Signal Manager user strategy/config calls, Market Regime config, and Premium sampling config switched to `authFetch`; remaining Signal Manager bare fetches are public market K-line preview reads; frontend production build passed.
- Passed: Membership isolation smoke test in `uv run`: Alice sync/logout did not alter Bob's subscription and spoofed frontend username was ignored.
- Passed: `user_routes.py` syntax compile in both system Python and `uv run` backend environment after membership isolation fix.
- Warning only: Vite reported stale browser baseline data and large bundle chunks.
- Blocked: `git push -u origin codex/ai-agent-multitenant-foundation` failed with `could not read Username for 'https://github.com': Device not configured`.

## Known Not-Accepted Items

- Real Casdoor JWKS/issuer/audience environment values still need to be configured and accepted with a live login token.
- Redis/distributed job queue execution is not implemented in this slice; DB persistence covers single-server task/chunk recovery, not multi-instance worker orchestration.
- End-to-end browser acceptance with real logged-in Hyper Insight sessions is still pending.
- Real exchange execution acceptance is still pending; this slice adds automated hard-risk preflight but does not execute a live order for validation.
