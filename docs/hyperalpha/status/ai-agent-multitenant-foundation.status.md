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
- Account-owner-scoped premium checks for Binance mainnet quotas and Hyperliquid builder fee decisions.
- User-scoped Telegram/Discord bot credential API and bot notification configuration reads/writes.
- User-scoped legacy paper/order-matching API reads, manual execution, cancellation, processing, and health counts.
- User-scoped trader data export/import account ownership validation.
- User-scoped Hyperliquid exchange action log reads and stats.
- User-scoped sampling preferences with effective global sampling pool aggregation.
- User-scoped custom factor library CRUD and Hyper AI `save_factor` tool ownership.
- User API list/login hardening for To C identity isolation.
- User-scoped Prompt Backtest task/list/status/results/item/import/delete/retry lifecycle.
- User-scoped Analytics summary/by-dimension/trade-detail/replay/program-analytics reads.
- User-bound WebSocket bootstrap/account switching/order/snapshot/asset-curve requests and per-user asset-curve broadcasts.
- Required-auth guard for system log reads/deletes and generic system config writes; generic config writes are limited to `ui_language`.
- Required-auth guard for system data management endpoints and news source management endpoints.
- Required-auth guard for Market Regime configuration and Signal analysis/runtime-state tool endpoints.
- Development progress and acceptance markers.
- REST manual order-placement APIs are not changed in this slice; WebSocket order placement now validates the connection user's account ownership.

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
| Premium entitlement isolation | Done | AI Trader, Program Trader, Binance API, and Hyperliquid builder fee checks use the account owner's subscription instead of any premium user in the database |
| Bot config API isolation | Done | `bot_configs.user_id` migration/model/service/API plus frontend `authFetch` prevent users from overwriting each other's Telegram/Discord credentials or notification toggles |
| Legacy order route isolation | Done | `/api/orders/*` resolves current user, validates order/account ownership, scopes pending/list/detail/cancel/execute/process/health, and no longer trusts URL/body `user_id` for access |
| Trader data import/export isolation | Done | Trader export/import preview/execute validate target `account_id` belongs to current user before reading or writing decision/trade data |
| Hyperliquid action log isolation | Done | `/api/hyperliquid/actions` joins `accounts` and filters entries/stats to the current user's accounts |
| Sampling preference isolation | Done | `/api/config/global-sampling` stores current-user preferences; effective global pool config uses max depth and min interval across user preferences |
| Custom factor ownership | Done | CustomFactor `user_id` migration/model/API and Hyper AI `save_factor` store/list/edit/delete only the current user's custom factors while built-in expression factors remain global |
| User API hardening | Done | Legacy `/api/users/login` validates `password_hash`; `/api/users/` returns only the current request user |
| Prompt Backtest ownership | Done | Backtest task creation validates account owner; task/list/status/results/item/import/delete/retry endpoints are current-user scoped; import reads original logs only from the task account |
| Analytics ownership | Done | Summary/by-strategy/by-account/by-symbol/by-operation/by-trigger/by-factor/trades/replay/kline/program analytics endpoints filter by current-user accounts and reject cross-user `account_id` filters |
| WebSocket ownership | Done | WS resolves session/JWT identity from query/header/message token, ignores client-provided username for bootstrap, rejects cross-user `switch_account`, scopes asset curves by current user, and sends auth tokens from frontend WS requests |
| Global config/log auth | Done | `get_authenticated_user_dependency` requires a real session/JWT for system logs and generic config updates; `/api/config/{key}` only permits `ui_language` |
| System/news management auth | Done | Storage stats, data coverage, retention, backfill, news source config/test/stats endpoints require real session/JWT; Settings data-management requests use auth-aware fetch |
| Signal/regime tool auth | Done | Market Regime config list/update plus Signal metric analysis/state/reset endpoints require real session/JWT |
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
- Passed: Premium account-owner smoke test in `uv run`: Bob premium did not make Alice premium for Binance quota checks or Hyperliquid builder fee, while Bob retained premium behavior.
- Passed: Static search found no remaining `User.username != 'default'` premium checks in backend API/services.
- Passed: Premium-related trading service syntax compile in both system Python and `uv run` backend environment.
- Passed: Bot config isolation smoke test in `uv run` with a test encryption key: Alice/Bob Telegram configs and notification configs did not overwrite each other.
- Passed: Bot model/service/routes/migration syntax compile in both system Python and `uv run` backend environment; frontend production build passed after Bot config requests switched to `authFetch`.
- Passed: Legacy order route isolation smoke test in `uv run`: Bob could not read Alice's order, pending orders and health counts were current-user scoped.
- Passed: Legacy order route re-smoke after create-order compatibility adjustment for body `session_token`/password auth.
- Passed: Order route/model syntax compile in both system Python and `uv run` backend environment.
- Passed: Trader data owner isolation smoke test in `uv run`: Alice could preview import into her trader; Bob received 404 for Alice's trader.
- Passed: Trader data route syntax compile in both system Python and `uv run` backend environment.
- Passed: Hyperliquid action owner isolation smoke test in `uv run`: Alice action stats excluded Bob's action; Bob filtering Alice account returned no entries.
- Passed: Hyperliquid action route syntax compile in both system Python and `uv run` backend environment.
- Passed: Sampling config isolation smoke test in `uv run`: Bob lowering his depth did not reduce Alice's effective depth; effective global depth/interval recomputed from user preferences.
- Passed: Sampling config route/model/migration syntax compile in both system Python and `uv run` backend environment.
- Passed: Custom factor owner isolation smoke test in `uv run`: Alice/Bob could save same custom factor name independently; Alice library excluded Bob private factor; Alice could not delete Bob factor.
- Passed: Custom factor route/model/migration/tool syntax compile in both system Python and `uv run` backend environment.
- Passed: User login/list smoke test in `uv run`: wrong password rejected, correct password created a session, user listing returned only current user.
- Passed: User route/repository syntax compile in both system Python and `uv run` backend environment.
- Passed: Prompt Backtest owner isolation smoke test in `uv run`: Alice saw only her task, Bob received 404 for Alice task/item, and dirty task items could not import Bob's original decision log reason.
- Passed: Prompt Backtest route syntax compile in both system Python and `uv run` backend environment.
- Passed: Analytics owner isolation smoke test in `uv run`: Alice summary/account/trade/replay reads excluded Bob's trade PnL/order, Bob replaying Alice trade returned 404, and Bob filtering Alice account returned 404.
- Passed: Program analytics owner isolation smoke test in `uv run`: Alice program summary/by-program excluded Bob's ProgramExecutionLog, and Bob filtering Alice account returned 404.
- Passed: Analytics route syntax compile in both system Python and `uv run` backend environment.
- Passed: WebSocket owner isolation smoke test in `uv run`: Bob could not pass the WS account owner guard for Alice's account, Alice/default asset curves returned only their own account rows.
- Passed: Frontend WS auth static check: remaining `send(JSON.stringify(...))` calls in the main app and asset-curve component go through `withWsAuth`.
- Passed: WebSocket route syntax compile in both system Python and `uv run` backend environment; frontend production build passed after WS token propagation.
- Passed: Required config auth smoke test in `uv run`: anonymous required-auth resolution returned 401, `ui_language` update succeeded for an authenticated user, and `hyperliquid_trading_mode` generic update returned 403.
- Passed: Auth/config/system-log route syntax compile in both system Python and `uv run` backend environment; frontend production build passed after Settings language update switched to `authFetch`.
- Passed: System/news management static required-auth check: storage/data coverage/retention/backfill and news source management handlers all depend on `get_authenticated_user_dependency`.
- Passed: System/news route syntax compile in both system Python and `uv run` backend environment; frontend production build passed after Settings system-data requests switched to `authFetch`.
- Passed: Market Regime/Signal required-auth static check: config list/update, metric analysis, signal state read, and signal state reset handlers all depend on `get_authenticated_user_dependency`.
- Passed: Market Regime/Signal route syntax compile in both system Python and `uv run` backend environment.
- Warning only: Vite reported stale browser baseline data and large bundle chunks.
- Warning only: Analytics smoke used a fake snapshot session because local `SNAPSHOT_DATABASE_URL` default Postgres was not reachable during test.
- Warning only: WebSocket smoke used a fake snapshot session because local `SNAPSHOT_DATABASE_URL` default Postgres was not reachable during test.
- Blocked: `git push -u origin codex/ai-agent-multitenant-foundation` failed with `could not read Username for 'https://github.com': Device not configured`.

## Known Not-Accepted Items

- Real Casdoor JWKS/issuer/audience environment values still need to be configured and accepted with a live login token.
- Redis/distributed job queue execution is not implemented in this slice; DB persistence covers single-server task/chunk recovery, not multi-instance worker orchestration.
- End-to-end browser acceptance with real logged-in Hyper Insight sessions is still pending.
- Real exchange execution acceptance is still pending; this slice adds automated hard-risk preflight but does not execute a live order for validation.
- Telegram/Discord external bot long-connection routing is not fully multi-tenant yet; this slice scopes stored credentials and notification config, but concurrent per-user bot runtimes/webhook dispatch still need a dedicated design.
- Factor computation/value storage is still global by factor name; custom factor CRUD is user-scoped, but per-user computed factor values need a dedicated schema if private custom factors should be precomputed.
- Admin RBAC is not implemented yet; newly required-auth system log/config endpoints require a real user token but do not distinguish operators/admins from ordinary authenticated users.
