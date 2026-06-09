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
- Program response binding counts include only current-owner, non-deleted account bindings.
- Program Backtest result, trigger, marker, and trigger-detail routes resolve backtests through current-user program/account/binding ownership.
- Program AI backtest-history tool validates current-user program/account ownership before exposing backtest summaries.
- Program AI backtest trigger list/detail tools validate current-user program/account ownership before exposing trigger snapshots.
- Program AI quick strategy verification validates current-user SignalPool ownership before using signal-triggered backtests.
- User-scoped Kline AI analysis creation, history, and detail reads.
- User-scoped K-line data service exchange resolution and backfill task visibility/deletion.
- User-scoped account dashboard/config/action routes and asset curve reads.
- User-scoped Binance wallet/config/manual-action routes and per-user quota/premium checks.
- User-scoped Arena trades, model chat, position, analytics, PnL status reads, and PnL update action.
- User-scoped PromptTemplate, SignalDefinition, and SignalPool ownership.
- Prompt binding repository reads/writes/deletes support account-owner guards for Prompt API, Hyper AI tools, and AI decision prompt resolution.
- User-scoped Hyper Insight wallet-tracking runtime config, token sync, websocket state, and wallet-signal callbacks.
- Hyper AI destructive tools validate current-user ownership before calling shared delete services.
- Shared entity deletion services accept owner context and refuse cross-user deletes for traders, prompts, signals, signal pools, programs, and bindings.
- Hyper AI tool execution, harness calls, sub-agent calls, and chat streams fail closed when authenticated user context is missing.
- Hyper AI direct tool functions no longer default to user `1`; protected direct calls require explicit user context.
- Hyper AI trader-list tool renders only current-user/system prompt bindings and current-user program bindings.
- Hyper AI trader diagnostics treat only current-user/system prompt templates and current-user programs as valid trader strategy bindings.
- Hyper AI strategy list/detail bound-trader displays include only current-user, non-deleted accounts.
- Hyper AI program-binding update tool validates both current-user account and current-user program ownership.
- Hyper AI harness dynamic risk preflight checks active prompt/program/signal-pool bindings only inside the current user's trader boundary.
- Hyper AI external tool config registry requires explicit user context and never reads or writes the first profile by fallback.
- Hyper AI profile and LLM config reads require explicit user context and no longer fall back to the first stored profile.
- Hyper AI conversation helper reads, message writes, and LLM context construction validate conversation ownership.
- Hyper AI memory helper reads, saves, updates, deletes, and `save_memory` tool writes require explicit user context.
- Prompt, Signal, Program, Attribution, and Kline AI service entry points reject missing user context and validate AI account ownership.
- Attribution AI internal tool calls list, summarize, and inspect only the current user's accounts, signal pools, signals, and decision logs.
- Prompt/Program shared AI tools list and inspect only the current user's signal pools, prompt context, trader details, decision statistics, decision lists, and decision snapshots.
- Signal AI tool execution receives current user context so factor indicators resolve the user's private factor library.
- Hyper AI tool-call streams and persisted tool logs mask sensitive arguments such as API keys, secrets, tokens, private keys, and passwords.
- Hyper AI frontend tool detail rendering masks sensitive arguments from legacy or malformed stored tool logs.
- AI stream polling tasks are owner-scoped so users can only poll, inspect, or confirm their own background AI tasks.
- AI stream polling tasks and chunks are persisted to the database for single-server restart recovery.
- AI stream task admission has global and per-user running-task limits for single-server DeepSeek/Qwen capacity isolation.
- AI stream admission can optionally use Redis-backed distributed leases for multi-instance global/per-user capacity isolation.
- AI stream polling can read active remote-instance running tasks from DB chunks when a Redis lease is still alive.
- AI stream high-risk tool confirmations are persisted so a confirmation submitted to one backend instance can wake the instance running the Agent task.
- Same-user same-conversation AI task admission can reuse an active remote-instance running task when its Redis lease is still alive.
- AI stream local/Redis admission environment variables are documented in root and backend `.env.example` templates.
- AI stream task IDs use UUID entropy to avoid multi-user/multi-request collisions under high concurrency.
- Admin-only AI runtime visibility shows shared model capacity, queue depth, and per-user buffered task occupancy.
- Admin-only AI runtime visibility shows optional Redis distributed admission status, lease count, and lease TTL.
- Admin-only AI runtime visibility distinguishes local, remote, effective, persisted, and stale AI running tasks across backend instances.
- Hyper AI and Program AI task admission is conversation-scoped, so one conversation cannot run overlapping writes while other users/conversations can still run.
- Context compression memory extraction stores long-term memories under the current user.
- User-scoped Hyperliquid/Binance symbol watchlists, with shared data collectors reading the aggregate symbol union.
- User-scoped exchange preference selection so one user's Hyperliquid/Binance/Aster choice does not overwrite another user's UI state.
- Hyperliquid account, wallet, manual order, action summary, and wallet upgrade APIs validate current-user account ownership.
- Hyperliquid execution environment defaults to account-level settings for setup, switching, AI decisions, Program Trader, and trading commands.
- Hyperliquid environment shared service functions accept owner guards for setup, switching, config, client, leverage, enable, and disable operations.
- Program Trader execution passes account owner into Hyperliquid environment, client, leverage, and wallet environment lookups.
- Program Trader signal and scheduled execution skip inactive/deleted accounts, inactive/deleted bindings, deleted programs, and cross-owner account/program bindings; order-result log updates must match the current binding/account.
- AI Trader decision and trading command paths pass account owner into Hyperliquid environment, client, and leverage lookups.
- Account, Arena, Prompt, WebSocket, Hyper AI, Program preview, and snapshot paths pass owners into Hyperliquid client creation.
- Strategy manager loads non-deleted account owners and passes request owner into scheduled/signal AI Trader exchange execution.
- Strategy repository read/list/upsert/last-trigger helpers support owner guards for account strategy configuration.
- Trading command AI prompts use each account owner's watchlist instead of a cross-user aggregate list.
- Automated AI Trader and Program Trader order execution pass a shared hard risk validator before exchange order placement.
- Auth-aware Hyper AI, Signal AI, Prompt AI, Program AI, Attribution AI, Program Trader, Program Backtest, Kline AI, Prompt Manager, and Signal Manager frontend requests.
- Auth-aware Attribution analytics and Trade Replay frontend requests.
- Auth-aware trading account, strategy, wallet, asset-curve, Arena model-chat, and action-log frontend requests.
- AI Trader LLM API keys are masked in account API responses and are not overwritten by masked frontend echoes.
- AI Trader creation requires an explicit model, Base URL, and API key instead of storing a placeholder key.
- New AI Traders default to auto-trading disabled until the user explicitly enables Start Trading.
- Legacy `/api/accounts` account management routes expose and update `auto_trading_enabled` consistently with safe-start defaults.
- Legacy `/api/accounts` updates preserve existing API keys when clients echo masked key responses.
- Legacy account repository update, cash update, activate, and deactivate helpers support owner guards for session-token account routes.
- Legacy account repository reads support owner guards; account-management and WebSocket owner checks use guarded account reads.
- Auth-aware identity runtime token, membership sync, Signal Manager strategy-analysis, market-regime config, factor analysis, and premium sampling-config requests.
- Auth-aware frontend watchlist reads for Klines, Arena NewsZone, Signal Manager, and Dashboard Insight.
- User-scoped membership sync and logout clearing so one user cannot overwrite or delete other users' premium status.
- Account-owner-scoped premium checks for Binance mainnet quotas and Hyperliquid builder fee decisions.
- User-scoped Telegram/Discord bot credential API and bot notification configuration reads/writes.
- User-scoped Telegram webhook secret routing, per-user Telegram polling tasks, bot chat bindings, bot conversations, and AI/event notifications.
- User-scoped Discord Gateway runtime clients for concurrent per-user bot long connections.
- User-scoped legacy paper/order-matching API reads, manual execution, cancellation, processing, and health counts.
- Legacy paper order matching service execution, cancellation, pending-order reads, and batch processing accept owner guards.
- Legacy order and position repository reads support owner guards for WebSocket snapshots and order execution broadcasts.
- Position valuation uses owner-scoped position reads for account, Arena, WebSocket, trading command, and AI decision paths.
- WebSocket snapshot Trade and AI decision log reads join account ownership and optional Hyperliquid environment filters.
- Account asset-curve and manual AI trigger trade reads join account ownership before returning Trade rows.
- Trader data export/import decision log reads and duplicate checks join account ownership.
- User-scoped trader data export/import account ownership validation.
- User-scoped Hyperliquid exchange action log reads and stats.
- User-scoped sampling preferences with effective global sampling pool aggregation.
- User-scoped custom factor library CRUD and Hyper AI `save_factor` tool ownership.
- Private custom factors are excluded from shared factor precomputation/effectiveness storage; resolver supports current-user private factor lookup.
- User API list/login hardening for To C identity isolation.
- User-scoped Prompt Backtest task/list/status/results/item/import/delete/retry lifecycle, original decision-log reads, and background system-prompt template resolution.
- User-scoped Analytics summary/by-dimension/trade-detail/replay/program-analytics reads and current-user program-name visibility.
- User-bound WebSocket bootstrap/account switching/order/snapshot/asset-curve requests and per-user asset-curve broadcasts.
- Arena trade feed and model-chat strategy-name lookups render only current-user/system prompt templates, current-user programs, and current-user signal pools.
- Required-auth guard for system log reads/deletes and generic system config writes; generic config writes are limited to `ui_language`.
- Required-auth guard for system data management endpoints and news source management endpoints.
- Background News AI classification uses platform-owned `NEWS_AI_LLM_*` environment variables and skips when unset instead of borrowing any user's Hyper AI key.
- Required-auth guard for Market Regime configuration and Signal analysis/runtime-state tool endpoints.
- Required-auth guard for resource-heavy Factor compute/evaluate/validate endpoints.
- Required-auth guard for Hyperliquid builder authorization status checks.
- Required-auth guard for standalone Hyper AI LLM connection tests.
- Admin RBAC guard for system logs, generic system config writes, system data management, and news source management.
- Admin-only user role-management API and Settings UI for To C operations access control.
- Admin role changes emit `admin_audit` system logs with actor, target, and old/new role metadata.
- Admin role changes persist to `admin_audit_logs` for restart-safe operational audit.
- Persistent admin audit logs are displayed in the Settings Admin UI for recent role changes.
- Current-user role is exposed to the frontend so non-admin users do not see Settings admin controls while backend RBAC remains authoritative.
- Backend route audit completed for account/analytics/AI/config/system/signal/factor management endpoints; remaining unauthenticated handlers are public market-data/static-doc/auth-lifecycle endpoints plus signed Telegram webhook ingress.
- Development progress and acceptance markers.
- REST manual order placement resolves the order owner from authenticated request context or a verified body session token; WebSocket order placement validates the connection user's account ownership.
- Manual AI trade trigger API passes the current user into trading command services; single-account execution filters by request owner while background global scheduling remains unchanged.
- Secondary account metadata lookups in Program execution feed and Binance wallet listing validate current-user ownership.

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
| Program response binding-count ownership | Done | Program list/detail/create/update responses count only owner-account, non-deleted bindings |
| Program Backtest route-helper ownership | Done | Result, trigger, marker, and trigger-detail routes reject backtests that do not resolve through current-user program/account/binding ownership |
| Program AI backtest-history ownership | Done | Backtest-history tool requires current-user program ownership and only reads current-user, non-deleted account bindings; legacy null-user backtests remain compatible through owned bindings |
| Program AI backtest trigger ownership | Done | Trigger list/detail tools require current-user program, account, binding, and compatible backtest ownership before returning trigger snapshots |
| Program AI quick verify signal-pool ownership | Done | `quick_verify_strategy` rejects cross-user/deleted signal pools before running the backtest engine and uses only current-user pool symbols |
| Attribution AI route filtering | Done | Chat/history endpoints use current user; `accountId` is ownership-checked |
| Kline AI route filtering | Done | Analysis creation validates account owner; history/detail use current user |
| K-line data/backfill user scoping | Done | K-line data routes resolve exchange from current user or explicit `exchange`; backfill tasks store `user_id` and are listed/statused/deleted by owner |
| Account route ownership | Done | Account list/overview/strategy/create/update/delete, LLM test, manual AI trigger, builder checks, disable-trading, dashboard visibility, and asset curve reads are scoped to current user |
| Binance route ownership | Done | Binance wallet setup/config/list/delete, balance, positions, manual order, close-position, summary, stats, limited binding, daily quota, and rebate checks are current-user guarded |
| Arena route ownership | Done | Arena trades, model-chat, model-chat snapshots, positions, analytics, PnL sync status, and PnL update action filter by current-user accounts |
| Strategy entity ownership | Done | `add_strategy_entity_user_scope.py`; PromptTemplate, SignalDefinition, SignalPool CRUD scoped by current user |
| Prompt binding repository owner guard | Done | `prompt_repo` binding read/upsert/delete/prompt-resolution helpers accept `owner_user_id`; Prompt API, Hyper AI binding tools, and AI decision service pass account/current owner |
| Hyper Insight runtime user scoping | Done | `add_hyper_insight_wallet_runtime_user_scope.py`; token/status/websocket state and wallet pool matching are user-scoped |
| AI tool user propagation | Done | Hyper AI tool execution passes `user_id` into subagents, wallet status, tracked wallet tools, Strategy Radar, `save_program`, `create_ai_trader`, and `web_search` config lookup |
| AI tool missing-user fail-closed | Done | Hyper AI dispatcher, harness, sub-agent dispatcher, and stream entry reject missing user context instead of falling back to user `1` |
| AI tool direct-call user context | Done | Hyper AI direct tool functions reject missing `user_id`; system logs are admin-gated; direct factor/trader tools are user-scoped |
| Hyper AI trader binding visibility | Done | `list_traders` resolves prompt names only from current-user/system templates and skips program bindings whose program is not owned by the current user |
| Hyper AI trader diagnostics binding ownership | Done | `diagnose_trader_issues` ignores dirty prompt/program bindings that point outside the current user's prompt/program boundary |
| Hyper AI strategy bound-trader ownership | Done | `list_strategies` detail and list modes join prompt/program bindings through current-user, non-deleted accounts |
| Hyper AI program-binding update ownership | Done | `update_program_binding` rejects bindings whose account or program does not resolve to the current user |
| Hyper AI harness owner-scoped risk preflight | Done | `assess_tool_risk` receives current `user_id`, treats missing user context as high risk, and evaluates active prompt/program/signal-pool bindings only for that user's traders |
| AI external tool config isolation | Done | `hyper_ai_tool_registry` requires explicit `user_id`; Tavily/API key configs read/write only the current user's Hyper AI profile |
| Hyper AI profile no implicit fallback | Done | `get_or_create_profile(None)` fails closed; `get_llm_config(None)` returns unconfigured with `missing_user_context` instead of reading the first profile |
| Hyper AI conversation helper ownership | Done | Conversation creation/read helpers require user context; message writes and LLM context building reject conversations not owned by that user |
| Hyper AI memory helper ownership | Done | Memory read/add/update/delete/limit helpers require user context; `save_memory` tool passes current `user_id` and blocks missing context |
| Sub-agent service user context | Done | Prompt/Signal/Program/Attribution/Kline service entry points reject missing `user_id` and cross-user AI account access |
| Attribution AI tool ownership | Done | Function-calling tools receive `user_id`; account list, attribution summary, strategy, prompt template, signal pool, trade chain, and factor attribution are current-user scoped |
| Prompt/Program shared tool ownership | Done | Shared signal pool/backtest, prompt context, trader details, decision stats/list/detail, and factor query tools receive `user_id`; decision log reads join account ownership |
| Signal AI tool user context | Done | Signal AI function-calling executor blocks missing `user_id` and passes current user into factor indicator resolution |
| AI tool argument masking | Done | User-visible `tool_call` events and persisted `tool_calls_log` store masked sensitive args while tools still receive original args for execution |
| AI tool frontend display masking | Done | Hyper AI tool detail UI recursively masks sensitive args before rendering, including legacy stored logs |
| AI delete tool ownership guard | Done | Trader, prompt, signal, pool, program, and binding delete tools validate current-user ownership before deletion |
| Entity deletion service owner guard | Done | Shared delete service functions accept `owner_user_id`; API routes and Hyper AI delete tools pass current user into service-layer deletion |
| AI stream task ownership | Done | Stream tasks store `user_id`; poll/status/confirmation endpoints enforce current-user access |
| AI stream task persistence | Done | `add_ai_stream_persistence.py`; stream tasks/chunks are persisted and stale running tasks hydrate as interrupted after restart |
| AI stream task admission limits | Done | `AI_STREAM_MAX_RUNNING_GLOBAL` and `AI_STREAM_MAX_RUNNING_PER_USER` cap shared LLM task concurrency before model calls are submitted |
| AI stream distributed admission leases | Done | Optional `AI_STREAM_REDIS_URL` Redis leases share global/per-user admission limits across backend instances while no-Redis deployments keep local admission |
| AI stream remote running hydration | Done | Running tasks found in DB stay running only when a Redis lease is active; remote pollers refresh DB chunks while stale running rows become interrupted |
| AI stream distributed confirmations | Done | `ai_stream_confirmations` stores high-risk tool checkpoint responses; waiters use local `Event` plus DB polling so cross-instance confirmations can unblock the running task |
| AI stream conversation duplicate guard | Done | `get_pending_task_for_conversation` checks persisted running tasks and active Redis leases so same-user same-conversation starts can return `already_running` across backend instances |
| AI stream runtime env templates | Done | Root and backend `.env.example` include worker, local admission, persistence, Redis URL, lease TTL, key prefix, and fail-open settings |
| AI stream task ID entropy | Done | `generate_task_id()` keeps the readable prefix/timestamp and adds UUID entropy to prevent same-thread same-millisecond collisions |
| AI runtime admin visibility | Done | Admin-only `/api/ai-stream/admin/runtime` plus Settings AI Runtime section expose shared capacity, queue depth, and per-user task occupancy without message/tool payloads |
| AI runtime distributed-admission visibility | Done | Admin runtime stats and Settings AI Runtime display show distributed admission enablement, availability, Redis leases, and lease TTL without exposing Redis URL |
| AI runtime remote-task visibility | Done | Admin runtime stats and Settings AI Runtime display local/effective/remote running counts plus persisted/stale DB running tasks for multi-instance operations |
| Conversation task admission | Done | Hyper AI and Program AI return `already_running` for the same user's active conversation task while allowing other users/conversations to start under capacity limits |
| Compression memory ownership | Done | `compress_messages(..., user_id=...)` propagates current user into background memory extraction |
| Symbol watchlist ownership | Done | `add_user_symbol_watchlists.py`; Hyperliquid/Binance watchlists are stored per user, with aggregate reads for collectors |
| Watchlist API/AI tool scoping | Done | `/symbols/watchlist` GET/PUT and Hyper AI `get_watchlist/update_watchlist` pass current `user_id` |
| Exchange preference ownership | Done | `/api/users/exchange-config` reads/writes `UserExchangeConfig` by resolved request user; frontend `ExchangeContext` uses `authFetch` |
| Trading command watchlist isolation | Done | Hyperliquid/Binance AI prompts use each account owner's watchlist while price collectors use the union |
| Hyperliquid API ownership guard | Done | Account-level Hyperliquid config, balance, positions, manual order, wallet, agent wallet, actions summary, and upgrade-check APIs validate current user |
| Hyperliquid account execution environment | Done | Setup/switch/client defaults, AI decision logs, Program Trader, and trading commands use account-level environment before global fallback |
| Hyperliquid environment service owner guard | Done | Shared setup/switch/config/client/leverage/enable/disable helpers accept `owner_user_id`; Hyperliquid API routes pass current user into service calls |
| Program Trader Hyperliquid owner propagation | Done | Program execution environment, client, leverage, and wallet lookups pass the binding account owner into Hyperliquid service helpers |
| Program Trader scheduled/signal/log guard | Done | Signal-trigger and scheduled binding reloads require active, non-deleted accounts/bindings and current-owner programs; order-result updates require matching execution `log_id`, `binding_id`, and `account_id` |
| AI Trader Hyperliquid owner propagation | Done | AI decision prompt/context and trading command execution pass account owner into Hyperliquid environment, client, and leverage helpers |
| Remaining Hyperliquid client owner propagation | Done | Account, Arena, Prompt, WebSocket, Hyper AI, Program preview, and snapshot callers pass account/current user into `get_hyperliquid_client` |
| Strategy manager owner propagation | Done | Strategy refresh skips deleted accounts, stores account owner in `StrategyState`, and scheduled/signal triggers pass owner into Hyperliquid/Binance AI Trader execution |
| Strategy repository owner guard | Done | Strategy read/list/upsert/last-trigger helpers accept `owner_user_id`; account API, Hyper AI, Prompt shared tools, and AI decision persistence pass current account owner |
| Automated execution hard risk guard | Done | `hard_risk_service.py`; AI Trader and Program Trader reject orders exceeding hard leverage, single-trade margin, projected margin usage, optional TP/SL, or TP/SL side rules |
| Frontend token propagation | Done | `authFetch`/auth-aware `apiRequest` used by Hyper AI, onboarding, Signal AI, Prompt AI, Program AI, Attribution AI chat, Program Trader, Program Backtest, Kline AI, Prompt Manager, Signal Manager, and polling |
| Frontend attribution analytics auth | Done | Attribution summary/dimension/trade list/account list plus Trade Replay kline/replay/chat-stream requests use `authFetch` |
| Frontend trading account auth | Done | Binance wallet setup/status/balance/quota/delete, account strategy, asset curve, Arena model-chat, account deletion, and Hyperliquid action logs use `authFetch` |
| AI Trader API key response masking | Done | Account list/create/update responses return masked API keys plus `api_key_configured`; masked echoes are ignored on update and frontend edit forms preserve existing keys unless a new key is entered |
| AI Trader explicit key creation | Done | New AI Trader forms start with an empty credential draft, require model/Base URL/API key before test-and-create, and clear unsaved drafts on cancel/open |
| AI Trader safe start default | Done | Frontend, account API, and repository account creation default `auto_trading_enabled` to false; existing accounts are not changed |
| Legacy account auto-trading field | Done | `/api/accounts` create/update/list/detail/default responses include `auto_trading_enabled`; create/default remain paused unless explicitly enabled |
| Legacy account masked key preservation | Done | Repository updates ignore short masked API key echoes like `****1234`/`********1234` while accepting fresh keys |
| Legacy account repository owner guard | Done | `account_repo` update/cash/activate/deactivate helpers accept `owner_user_id`; session-token account routes pass the verified user |
| Legacy account repository read owner guard | Done | `get_account` accepts `owner_user_id`; account-management detail/update/delete and WebSocket account registration/order creation use owner-guarded reads |
| Frontend identity/signal config auth | Done | Auth runtime token sync, membership sync/clear, Signal Manager analysis/config, Market Regime config, factor evaluation, and premium sampling config use `authFetch` |
| Frontend watchlist auth | Done | Klines, Arena NewsZone, Signal Manager, and Dashboard Insight use auth-aware watchlist fetches |
| Membership sync isolation | Done | `/api/users/sync-membership` and `/api/users/clear-membership` update/delete only the current request user's `UserSubscription` |
| Premium entitlement isolation | Done | AI Trader, Program Trader, Binance API, and Hyperliquid builder fee checks use the account owner's subscription instead of any premium user in the database |
| Bot config API isolation | Done | `bot_configs.user_id` migration/model/service/API plus frontend `authFetch` prevent users from overwriting each other's Telegram/Discord credentials or notification toggles |
| Bot webhook/session isolation | Done | Telegram webhook secrets route inbound updates to one user's token/conversation; Telegram polling runs per user; BotChatBinding and system-event push are user-scoped |
| Discord gateway isolation | Done | Discord Gateway clients, loops, message handlers, status, disconnect, startup restore, and progress messages are keyed by owner user |
| Legacy order route isolation | Done | `/api/orders/*` resolves current user, validates order/account ownership, scopes pending/list/detail/cancel/execute/process/health, and no longer trusts URL/body `user_id` for access |
| REST order creation ownership | Done | `/api/orders/create` accepts body `user_id` only as a consistency check against the authenticated user or verified body `session_token`; default fallback cannot set another user's first trading password |
| Legacy order matching service owner guard | Done | `check_and_execute_order`, `cancel_order`, `get_pending_orders`, and `process_all_pending_orders` accept `owner_user_id`; user API paths pass current user while scheduler keeps global processing |
| Legacy order/position repository owner guard | Done | `list_orders`, `get_order_by_no`, `list_positions`, and `get_position` accept `owner_user_id`; WebSocket snapshots and order execution broadcasts pass account owner |
| Position valuation owner guard | Done | `calc_positions_value` accepts `owner_user_id`; account, Arena, WebSocket, trading command, and AI decision callers pass account owner |
| WebSocket snapshot log owner guard | Done | Paper/optimized/Hyperliquid WS snapshots use owner-scoped helper queries for `Trade` and `AIDecisionLog`, with environment filtering where relevant |
| Account API trade owner guard | Done | Account asset curve reconstruction and manual AI trigger recent-trade response use owner-scoped `Trade` helper queries |
| Trader data decision log owner guard | Done | Trader export decision-log reads and import duplicate checks use owner-scoped `AIDecisionLog` helper queries |
| Manual AI trade trigger service ownership | Done | `trigger-ai-trade` passes `request_user_id`; crypto, Hyperliquid, and Binance single-account execution stop before price/order work when the requested account is not owned by that user |
| Secondary account metadata lookup ownership | Done | Program execution feed and Binance wallet list re-check current-user ownership when resolving account names from already-scoped rows |
| Trader data import/export isolation | Done | Trader export/import preview/execute validate target `account_id` belongs to current user before reading or writing decision/trade data |
| Hyperliquid action log isolation | Done | `/api/hyperliquid/actions` joins `accounts` and filters entries/stats to the current user's accounts |
| Sampling preference isolation | Done | `/api/config/global-sampling` stores current-user preferences; effective global pool config uses max depth and min interval across user preferences |
| Custom factor ownership | Done | CustomFactor `user_id` migration/model/API and Hyper AI `save_factor` store/list/edit/delete only the current user's custom factors while built-in expression factors remain global |
| Private factor precompute guard | Done | Shared factor computation/effectiveness now processes only public `builtin_expression` rows; private custom factors resolve only with `user_id` for runtime/on-demand use |
| User API hardening | Done | Legacy `/api/users/login` validates `password_hash`; `/api/users/` returns only the current request user |
| Prompt Backtest ownership | Done | Backtest task creation validates account owner; task/list/status/results/item/import/delete/retry endpoints are current-user scoped; original decision-log reads join account ownership; background prompt resolution rejects cross-user private templates |
| Analytics ownership | Done | Summary/by-strategy/by-account/by-symbol/by-operation/by-trigger/by-factor/trades/replay/kline/program analytics endpoints filter by current-user accounts, reject cross-user `account_id` filters, and avoid cross-user program-name fallbacks |
| WebSocket ownership | Done | WS resolves session/JWT identity from query/header/message token, ignores client-provided username for bootstrap, rejects cross-user `switch_account`, scopes asset curves by current user, and sends auth tokens from frontend WS requests |
| Arena strategy-name visibility | Done | Arena trade feed and model-chat batch name lookups filter prompt templates by current-user/system visibility, programs by current user, and signal pools by current user |
| Global config/log auth | Done | `get_authenticated_user_dependency` requires a real session/JWT for system logs and generic config updates; `/api/config/{key}` only permits `ui_language` |
| System/news management auth | Done | Storage stats, data coverage, retention, backfill, news source config/test/stats endpoints require real session/JWT; Settings data-management requests use auth-aware fetch |
| News AI platform LLM config | Done | Background News AI reads `NEWS_AI_LLM_BASE_URL`, `NEWS_AI_LLM_MODEL`, `NEWS_AI_LLM_API_KEY`, and `NEWS_AI_LLM_API_FORMAT`; unset env skips classification without using user-provided keys |
| Signal/regime tool auth | Done | Market Regime config list/update plus Signal metric analysis/state/reset endpoints require real session/JWT |
| Factor resource auth | Done | Factor compute estimate/trigger/progress plus expression evaluate/validate endpoints require real session/JWT |
| Builder check auth | Done | Hyperliquid builder authorization status endpoint requires real session/JWT before proxying external authorization checks |
| Hyper AI connection-test auth | Done | Standalone Hyper AI LLM connection-test endpoint requires real session/JWT before using user-submitted provider credentials |
| Backend route auth audit | Done | Remaining unauthenticated route list reviewed: public market data/factor read/ranking/news article/static docs/auth lifecycle remain intentionally public or legacy-session based; Telegram webhook ingress is signed and user-routed |
| Admin RBAC guard | Done | `users.role`, `get_admin_user_dependency`, env/JWT admin role sync, and admin-only system/log/config/news management endpoints |
| Admin role management | Done | Admin-only `/api/users/admin/users` list/update endpoints plus Settings `Admin Users` tab; local smoke test covers ordinary-user 403, role update, invalid role, and last-admin demotion guard |
| Admin role audit logging | Done | Role changes write `admin_audit` system logs; local smoke test verifies actor/target metadata, duplicate no-op behavior, category listing, and stats |
| Persistent admin audit logs | Done | `admin_audit_logs` model/migration plus admin-only list API; local smoke test verifies DB persistence, API serialization, system-log mirror, and same-role no-op behavior |
| Admin audit UI | Done | Settings Admin tab fetches `/api/users/admin/audit-logs?limit=20` and renders recent role changes; production build and API smoke passed |
| Frontend admin visibility | Done | `UserOut.role`, AuthContext local role hydration, and Settings Admin tab conditional rendering hide admin controls for ordinary users while keeping backend RBAC checks |
| Backend checks | Passed | `python3 -m py_compile` on changed backend files |
| Frontend checks | Passed | `corepack pnpm -C frontend build` |
| Local commit | Done | Current branch `HEAD` |
| Remote push | Blocked | Terminal GitHub HTTPS credentials unavailable |
| Acceptance | Partial | Multi-user AI foundation, Redis distributed admission leases, cross-instance AI confirmation mailbox, and automated hard-risk checks passed; live Casdoor env acceptance, distributed worker queue routing, and real exchange execution remain unaccepted |

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
- Passed: Prompt binding repository owner-guard smoke test in `uv run`: Alice cannot read/upsert/delete Bob account bindings or bind Bob private templates; owner-scoped prompt resolution hides dirty cross-user bindings while system/Alice templates remain available.
- Passed: Program response binding-count owner smoke test in `uv run`: Alice program responses count Alice's active-account binding only and exclude Bob account bindings, deleted-account bindings, and soft-deleted bindings.
- Passed: Program Backtest route-helper owner smoke test in `uv run`: Alice can read current-user and legacy null-user owned backtests, while Bob-owned, mismatched-user, cross-account, cross-program, deleted-account, and deleted-binding rows are rejected.
- Passed: Program AI backtest-history owner smoke test in `uv run`: Alice cannot read Bob's program backtests, dirty cross-user account bindings, deleted-account bindings, or mismatched-user backtest rows; legacy null-user rows remain visible only through Alice-owned bindings.
- Passed: Program AI backtest trigger list/detail owner smoke test in `uv run`: Alice can inspect her own and legacy null-user owned triggers, while Bob-owned, cross-account, cross-program, deleted-account, and mismatched-user backtests are rejected for both trigger list and trigger detail tools.
- Passed: Program AI quick verify signal-pool owner smoke test in `uv run`: Alice-owned pools enter the backtest engine with owner pool symbols, Bob/deleted pools are rejected before engine execution, and scheduled-only verification still works.
- Passed: Hyper Insight wallet runtime route/service compile and frontend build after per-user token/status/websocket scoping.
- Passed: Hyper AI delete tool ownership guard compile and whitespace check.
- Passed: Hyper AI missing-user-context smoke test in `uv run`: dispatcher, harness, sub-agent dispatcher, and stream entry returned blocked/error before touching DB/LLM/exchange work; static search found no remaining `user_id or 1` in the Hyper AI tool execution chain.
- Passed: Hyper AI direct tool user-context smoke test in `uv run`: missing direct tool user context was blocked, system logs required admin role, factor library output was scoped to the current user, and cross-user trader/factor access was rejected.
- Passed: Hyper AI trader-list visibility smoke test in `uv run`: Alice's trader list hid Bob's private prompt/program binding names while still showing Alice-owned and system prompt bindings.
- Passed: Hyper AI trader diagnostics binding-owner smoke test in `uv run`: dirty Bob prompt/program bindings on Alice's trader no longer satisfy `strategy_bound`, while system/Alice-owned bindings still pass and Bob's trader remains inaccessible.
- Passed: Hyper AI strategy bound-trader owner smoke test in `uv run`: strategy list, prompt detail, and program detail show only Alice's non-deleted trader bindings while excluding Bob and deleted-account bindings; Bob private strategies remain inaccessible.
- Passed: Hyper AI program-binding update owner smoke test in `uv run`: Alice can update an Alice-account/Alice-program binding, while dirty Alice-account/Bob-program and Bob-account bindings are rejected without changing their config.
- Passed: Hyper AI harness risk-preflight smoke test in `uv run`: active prompt/program/signal-pool bindings are high-risk only for the owning user, Bob's bindings do not elevate Alice's risk, and missing user context fails closed as high-risk.
- Passed: Hyper AI external tool registry smoke test in `uv run`: missing user context raised before profile lookup, Alice and Bob tool configs stayed isolated, and updating Alice's Tavily config did not modify Bob's config.
- Passed: Hyper AI profile user-context smoke test in `uv run`: no-user LLM config did not read the first stored profile, `get_or_create_profile(None)` failed closed, explicit user 2 read only user 2 profile config, and no-user suggestions returned an empty missing-context result.
- Passed: Hyper AI conversation ownership smoke test in `uv run`: Bob could not read Alice's messages, write into Alice's conversation, or build an LLM prompt from Alice's history; Bob's own conversation still read/wrote normally.
- Passed: Hyper AI memory ownership smoke test in `uv run`: missing user context was blocked, Alice could not update/delete Bob's memory, and the Hyper AI `save_memory` tool stored new memory under the current owner.
- Passed: Sub-agent user context smoke test in `uv run`: Prompt, Signal, Program, Attribution, and Kline AI service entry points blocked missing user context and rejected cross-user AI account access.
- Passed: Attribution AI tool user-context smoke test in `uv run`: missing tool user context was blocked, Alice saw only Alice's account list, Bob's account/pool/trade chain/factor attribution were rejected, and all-account attribution summary counted only Alice's decision logs.
- Passed: Prompt/Program shared tool user-context smoke test in `uv run`: signal pools, prompt context, trader details, decision list/detail, and signal backtest pool validation were scoped to the current user.
- Passed: Prompt/Program shared tool decision-log re-smoke in `uv run`: trader stats and decision lists join account ownership, excluding Bob and deleted-account decision logs even when IDs are passed directly.
- Passed: Signal AI tool user-context smoke test in `uv run`: missing tool user context was blocked and factor indicator execution passed the current `user_id` into `compute_factor_series`.
- Passed: Hyper AI tool argument masking syntax compile and smoke test in `uv run`: nested API key/token/secret args are masked, and static search confirms `tool_call` events plus `tool_calls_log` use `safe_fn_args`.
- Passed: Frontend production build after Hyper AI tool detail rendering masks sensitive nested args before display; static search confirms completed-message tool arg rendering goes through `maskToolArgsForDisplay`.
- Passed: Entity deletion owner guard smoke test in `uv run`: Alice could not delete Bob's trader, prompt, signal, signal pool, trading program, prompt binding, or program binding at the shared service layer.
- Passed: AI stream owner scoping route/service compile, whitespace check, and frontend production build.
- Passed: AI stream persistence models/migration/service syntax compile.
- Passed: AI stream admission smoke test in `uv run`: per-user limit rejected a third concurrent task for one user, global limit rejected the next task when global running count was full, and completing a task reopened capacity.
- Passed: AI stream admission syntax compile in both system Python and `uv run` backend environment for StreamBuffer plus Hyper AI, Prompt AI, Signal AI, Attribution AI, and Hyper AI service task entry points.
- Passed: AI stream distributed admission smoke test in `uv run`: fake distributed admission acquired/released/refreshed leases, enforced per-user/global limits, released Redis leases when local capacity rejected a task, and exposed distributed admission stats.
- Passed: Redis admission controller fake-client smoke test in `uv run`: controller parsed Redis script responses for accepted/user-limit/global-limit paths, refreshed and released leases, reported running lease stats, and cleaned expired global leases.
- Passed: AI stream remote running hydration smoke test in `uv run`: a DB running task with active Redis lease stayed running and refreshed newly persisted chunks on subsequent polls, while a running row without a lease was marked interrupted.
- Passed: AI stream persisted confirmation mailbox and owner guard smoke test in `uv run`: duplicate pending confirmations and cross-user submissions were rejected; a simulated remote backend submitted the owning user's response through the DB and the waiting task woke from the persisted response.
- Passed: AI stream cross-instance conversation duplicate guard smoke test in `uv run`: same-user same-conversation starts reused a remote active task with a live lease, cross-user tasks stayed isolated, and stale running records without leases were interrupted.
- Passed: AI runtime remote stats smoke test in `uv run`: admin runtime stats reported local, remote, effective, persisted, and stale running tasks and per-user remote occupancy from DB plus fake Redis leases.
- Passed: Frontend production build after Settings AI Runtime displayed distributed admission status, Redis leases, and lease TTL.
- Passed: AI stream runtime environment templates updated for single-server and Redis distributed admission configuration.
- Passed: AI stream task ID UUID smoke test in `uv run`: 5000 sequential task IDs with the same prefix were unique and preserved the expected prefix/timestamp/random-suffix shape.
- Passed: AI runtime admin stats syntax compile in both system Python and `uv run` backend environment for `ai_stream_service.py` and `ai_stream_routes.py`.
- Passed: AI runtime admin stats smoke test in `uv run`: in-memory Alice/Bob/anonymous tasks produced correct global running/completed/error totals, per-user occupancy, oldest-running age, and username enrichment from the admin endpoint.
- Passed: Frontend production build after adding the Settings AI Runtime capacity and per-user occupancy section.
- Passed: Conversation task admission syntax compile in `uv run` backend environment for Hyper AI routes, Program routes, and AI stream service.
- Passed: Conversation task admission smoke test in `uv run`: Hyper AI and Program AI returned `already_running` for the same user's running conversation task, and a different user with the same conversation id was allowed to start.
- Passed: Frontend production build after Hyper AI and Program AI rollback temporary UI messages when a conversation already has a running task or the backend rejects admission.
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
- Passed: Account API key masking syntax compile in both system Python and `uv run` backend environment for `account_routes.py`.
- Passed: Account API key masking smoke test in `uv run` with a stubbed snapshot dependency: create/list/update responses returned only masked keys, masked update echoes did not overwrite stored keys, omitted keys preserved the stored key, and a fresh key replaced it while remaining masked in the response.
- Passed: Frontend production build after SettingsDialog preserves existing API keys unless a new key is entered and redacts API keys from client console logging.
- Passed: Static search found no remaining `default-key-please-update-in-settings` placeholder in SettingsDialog/API account creation paths.
- Passed: Frontend production build after requiring explicit model/Base URL/API key for new AI Trader creation and clearing unsaved credential drafts.
- Passed: AI Trader safe-default smoke test in `uv run`: account API creation, repository creation, and default-account creation all defaulted `auto_trading_enabled` to false, and default-account creation stored an empty API key instead of a placeholder.
- Passed: Backend syntax compile and frontend production build after new AI Trader auto-trading defaults switched off.
- Passed: Legacy `/api/accounts` smoke test in `uv run`: create/list/update/default responses expose `auto_trading_enabled`, default creation is paused, explicit update to true is reflected, and API keys remain masked.
- Passed: Backend syntax compile after legacy account schemas/routes/repository accepted and returned `auto_trading_enabled`.
- Passed: Legacy masked API key preservation smoke test in `uv run`: masked update echoes preserved the stored key, fresh keys replaced it, and long real keys starting with stars were not treated as masks.
- Passed: Account repository owner guard smoke test in `uv run`: cross-user update/cash/deactivate/activate returned `None`, Bob's account stayed unchanged, and masked API key updates preserved the stored key.
- Passed: Account repository read owner guard smoke test in `uv run`: cross-user `get_account` returned `None`, owner reads succeeded, default no-owner reads stayed compatible, and soft-deleted accounts stayed hidden.
- Passed: AuthContext, Signal Manager user strategy/config calls, Market Regime config, and Premium sampling config switched to `authFetch`; remaining Signal Manager bare fetches are public market K-line preview reads; frontend production build passed.
- Passed: Membership isolation smoke test in `uv run`: Alice sync/logout did not alter Bob's subscription and spoofed frontend username was ignored.
- Passed: `user_routes.py` syntax compile in both system Python and `uv run` backend environment after membership isolation fix.
- Passed: Premium account-owner smoke test in `uv run`: Bob premium did not make Alice premium for Binance quota checks or Hyperliquid builder fee, while Bob retained premium behavior.
- Passed: Static search found no remaining `User.username != 'default'` premium checks in backend API/services.
- Passed: Premium-related trading service syntax compile in both system Python and `uv run` backend environment.
- Passed: Hyperliquid environment owner guard smoke test in `uv run`: cross-user setup/switch/config/environment/leverage/client/enable/disable service calls rejected before wallet/client side effects.
- Passed: Program execution owner propagation smoke test in `uv run`: Program Trader wallet environment lookup passes the binding account owner into Hyperliquid environment resolution.
- Passed: Program Trader scheduled/log guard smoke test in `uv run`: scheduled cache excludes inactive/deleted account bindings, scheduled trigger reload refuses deleted-account bindings, and order-result updates cannot mutate logs from another binding/account.
- Passed: Program Trader signal/scheduled binding owner smoke test in `uv run`: signal-trigger lookup, scheduled cache refresh, and scheduled reload execute only active Alice-account/Alice-program bindings while rejecting cross-owner, inactive/deleted account, deleted-program, inactive-binding, and deleted-binding rows.
- Passed: AI Trader Hyperliquid owner propagation syntax/static check: `ai_decision_service.py` and `trading_commands.py` compile, and remaining Hyperliquid helper calls pass `owner_user_id=account.user_id`.
- Passed: Remaining Hyperliquid client owner propagation syntax/static check: account, arena, prompt, WebSocket, Program preview, Hyper AI, and snapshot modules compile, with client calls passing account/current user.
- Passed: Strategy manager owner propagation smoke test in `uv run`: strategy refresh loaded only active owner accounts and scheduled/signal execution passed `request_user_id` into Hyperliquid/Binance AI Trader triggers.
- Passed: Strategy repository owner guard smoke test in `uv run`: read/list/upsert/last-trigger helpers isolated users and hid soft-deleted account strategies.
- Passed: Bot config isolation smoke test in `uv run` with a test encryption key: Alice/Bob Telegram configs and notification configs did not overwrite each other.
- Passed: Bot model/service/routes/migration syntax compile in both system Python and `uv run` backend environment; frontend production build passed after Bot config requests switched to `authFetch`.
- Passed: Bot webhook/session isolation smoke test in `uv run`: Alice/Bob Telegram webhook secrets differed, Alice's secret resolved only Alice's token, Alice's AI decision event created only Alice's Bot conversation/message, and push delivery used only Alice's Telegram token/chat binding.
- Passed: Bot webhook/session isolation syntax compile in both system Python and `uv run` backend environment for Bot API/routes/services/model/migration plus AI/Signal/Program notification callers.
- Passed: Discord gateway multi-client smoke test in `uv run` with a fake Discord client: two owner users had independent clients/tokens, sending via user 2 used user 2's token, stopping user 1 did not stop user 2, and stop-all cleared all clients.
- Passed: Discord gateway multi-client syntax compile in both system Python and `uv run` backend environment for Discord service, Bot routes, and startup restore.
- Passed: Legacy order route isolation smoke test in `uv run`: Bob could not read Alice's order, pending orders and health counts were current-user scoped.
- Passed: Legacy order route re-smoke after create-order compatibility adjustment for body `session_token`/password auth.
- Passed: REST order creation ownership smoke test in `uv run`: default fallback could not create for Alice or set Alice's first trading password, verified body `session_token` created only for the token owner, mismatched token/user pairs were rejected, and same-user password flow still worked.
- Passed: Order matching owner guard smoke test in `uv run`: cross-user execute/cancel returned false without market-price side effects or frozen-cash mutation, and pending batch processing was scoped by user.
- Passed: Order/position repository owner guard smoke test in `uv run`: owner-scoped reads isolated Bob's order/position data from Alice, while legacy no-owner reads remained compatible.
- Passed: Asset calculator owner guard smoke test in `uv run`: cross-user position valuation returned zero without market-price side effects, while owner and legacy no-owner valuations remained compatible.
- Passed: WebSocket snapshot owner guard smoke test in `uv run`: trade and AI decision log helpers returned Bob's data only for Bob, returned none for Alice, and respected Hyperliquid environment filters.
- Passed: Account API trade owner guard smoke test in `uv run`: owner-scoped trade helper isolated users, respected sort/limit, and hid soft-deleted account trades.
- Passed: Trader data decision log owner guard smoke test in `uv run`: export helper and duplicate detection returned Bob's decisions only for Bob and hid soft-deleted account decisions.
- Passed: Trading command request-owner smoke test in `uv run`: Alice-triggered crypto, Hyperliquid, and Binance single-account execution for Bob's account stopped before price/symbol/order execution, while request-less scheduler semantics remain available.
- Passed: Order route/model syntax compile in both system Python and `uv run` backend environment.
- Passed: Secondary account metadata lookup syntax compile and static search after Program execution feed and Binance wallet list account-name lookups gained current-user filters.
- Passed: Trader data owner isolation smoke test in `uv run`: Alice could preview import into her trader; Bob received 404 for Alice's trader.
- Passed: Trader data route syntax compile in both system Python and `uv run` backend environment.
- Passed: Hyperliquid action owner isolation smoke test in `uv run`: Alice action stats excluded Bob's action; Bob filtering Alice account returned no entries.
- Passed: Hyperliquid action route syntax compile in both system Python and `uv run` backend environment.
- Passed: Sampling config isolation smoke test in `uv run`: Bob lowering his depth did not reduce Alice's effective depth; effective global depth/interval recomputed from user preferences.
- Passed: Sampling config route/model/migration syntax compile in both system Python and `uv run` backend environment.
- Passed: Custom factor owner isolation smoke test in `uv run`: Alice/Bob could save same custom factor name independently; Alice library excluded Bob private factor; Alice could not delete Bob factor.
- Passed: Custom factor route/model/migration/tool syntax compile in both system Python and `uv run` backend environment.
- Passed: Private factor precompute guard smoke test in `uv run`: public builtin expression factor was visible to global computation, Alice/Bob same-name private factors resolved only with matching `user_id`, and global computation/effectiveness ignored private factors.
- Passed: Private factor precompute guard syntax compile in both system Python and `uv run` backend environment for factor computation/effectiveness/resolver/routes/tools and runtime signal detection.
- Passed: User login/list smoke test in `uv run`: wrong password rejected, correct password created a session, user listing returned only current user.
- Passed: User route/repository syntax compile in both system Python and `uv run` backend environment.
- Passed: Prompt Backtest owner isolation smoke test in `uv run`: Alice saw only her task, Bob received 404 for Alice task/item, and dirty task items could not import Bob's original decision log reason.
- Passed: Prompt Backtest route syntax compile in both system Python and `uv run` backend environment.
- Passed: Prompt Backtest owner guard re-smoke in `uv run`: decision-log helpers hide Bob/deleted-account logs from Alice, import lookup returns only Alice-owned logs, system-prompt lookup ignores Bob's private template binding, and item result writes require matching task ownership.
- Passed: Analytics owner isolation smoke test in `uv run`: Alice summary/account/trade/replay reads excluded Bob's trade PnL/order, Bob replaying Alice trade returned 404, and Bob filtering Alice account returned 404.
- Passed: Program analytics owner isolation smoke test in `uv run`: Alice program summary/by-program excluded Bob's ProgramExecutionLog, and Bob filtering Alice account returned 404.
- Passed: Program analytics program-name visibility smoke test in `uv run`: Alice-owned logs with Bob program IDs return generic names instead of Bob's stored `program_name`, while Alice-owned and deleted-owned program names remain visible.
- Passed: Analytics route syntax compile in both system Python and `uv run` backend environment.
- Passed: Arena strategy-name visibility smoke test in `uv run`: owned decision rows do not display Bob's private prompt/program/signal-pool names, while Alice-owned and system prompt names remain visible.
- Passed: WebSocket owner isolation smoke test in `uv run`: Bob could not pass the WS account owner guard for Alice's account, Alice/default asset curves returned only their own account rows.
- Passed: Frontend WS auth static check: remaining `send(JSON.stringify(...))` calls in the main app and asset-curve component go through `withWsAuth`.
- Passed: WebSocket route syntax compile in both system Python and `uv run` backend environment; frontend production build passed after WS token propagation.
- Passed: Required config auth smoke test in `uv run`: anonymous required-auth resolution returned 401, `ui_language` update succeeded for an authenticated user, and `hyperliquid_trading_mode` generic update returned 403.
- Passed: Auth/config/system-log route syntax compile in both system Python and `uv run` backend environment; frontend production build passed after Settings language update switched to `authFetch`.
- Passed: System/news management static required-auth check: storage/data coverage/retention/backfill and news source management handlers all depend on `get_authenticated_user_dependency`.
- Passed: News AI LLM env config smoke test in `uv run`: unset `NEWS_AI_LLM_*` skips classification config, configured env returns platform-owned DeepSeek-style config, and `news_ai_classifier.py` no longer imports or calls Hyper AI `get_llm_config(db)`.
- Passed: System/news route syntax compile in both system Python and `uv run` backend environment; frontend production build passed after Settings system-data requests switched to `authFetch`.
- Passed: Market Regime/Signal required-auth static check: config list/update, metric analysis, signal state read, and signal state reset handlers all depend on `get_authenticated_user_dependency`.
- Passed: Market Regime/Signal route syntax compile in both system Python and `uv run` backend environment.
- Passed: Factor resource required-auth static check: compute estimate/trigger/progress and expression evaluate/validate handlers all depend on `get_authenticated_user_dependency`.
- Passed: Factor route syntax compile in both system Python and `uv run` backend environment.
- Passed: Builder authorization required-auth static check and account route syntax compile in both system Python and `uv run` backend environment.
- Passed: Hyper AI connection-test required-auth static check and route syntax compile in both system Python and `uv run` backend environment.
- Passed: Backend route auth audit scan: no remaining unauthenticated account/analytics/config/system/signal/factor compute/AI management route was left unclassified.
- Passed: Admin RBAC smoke test in `uv run`: admin session passed, ordinary session returned 403, anonymous returned 401, local `default` user promoted to admin, and unverified demo JWT with `roles=["admin"]` created an admin user.
- Passed: Admin RBAC syntax compile in both system Python and `uv run` backend environment for auth utilities, user repository, route modules, models, and migration.
- Passed: Admin RBAC static check: system, system-log, news source/stats, and generic system-config write endpoints now depend on `get_admin_user_dependency`.
- Passed: Admin role-management syntax compile in both system Python and `uv run` backend environment for user routes/auth utilities/user repository/models.
- Passed: Admin role-management smoke test in `uv run`: admin listed users, ordinary user received 403, role update to operator succeeded, invalid role returned 400, and the final admin/operator could not be downgraded.
- Passed: Frontend production build after adding the Settings `Admin Users` tab and role selector.
- Passed: Admin role audit syntax compile in both system Python and `uv run` backend environment for user routes, system-log routes, and system logger.
- Passed: Admin role audit smoke test in `uv run`: role update wrote one `admin_audit` warning with actor/target old/new role metadata, same-role update did not duplicate the log, and system-log categories/stats include `admin_audit`.
- Passed: Persistent admin audit syntax compile in both system Python and `uv run` backend environment for user routes, models, and migration.
- Passed: Persistent admin audit smoke test in `uv run`: role update wrote one `admin_audit_logs` row, admin-only audit API returned the serialized details, system-log mirror remained present, and same-role update did not duplicate persistence.
- Passed: Admin audit API re-smoke in `uv run`: role update created one persistent log and admin audit API returned actor/target old/new role fields for UI consumption.
- Passed: Frontend production build after adding the Settings Admin recent role-change audit section.
- Partial: Playwright opened the local Vite app at `http://127.0.0.1:5173/` and confirmed the app title/root rendered; Settings route remained behind startup initialization because no local backend/Postgres was running, with console errors limited to missing backend API/WS/static assets.
- Passed: User role exposure syntax compile in both system Python and `uv run` backend environment for user schema/routes/auth utilities.
- Passed: User role exposure smoke test in `uv run`: login, profile, and current-user list responses return the correct per-user role.
- Passed: Frontend production build after AuthContext local role hydration and conditional Settings Admin tab rendering.
- Warning only: Vite reported stale browser baseline data and large bundle chunks.
- Warning only: Analytics smoke used a fake snapshot session because local `SNAPSHOT_DATABASE_URL` default Postgres was not reachable during test.
- Warning only: WebSocket smoke used a fake snapshot session because local `SNAPSHOT_DATABASE_URL` default Postgres was not reachable during test.
- Blocked: `git push -u origin codex/ai-agent-multitenant-foundation` failed with `could not read Username for 'https://github.com': Device not configured`.

## Known Not-Accepted Items

- Real Casdoor JWKS/issuer/audience environment values still need to be configured and accepted with a live login token.
- Redis distributed admission leases and persisted high-risk confirmation responses are implemented for cross-instance capacity/confirmation coordination; distributed worker queue routing/execution is still not implemented in this slice.
- End-to-end browser acceptance with real logged-in Hyper Insight sessions is still pending.
- Real exchange execution acceptance is still pending; this slice adds automated hard-risk preflight but does not execute a live order for validation.
- Live Discord Gateway acceptance with real Discord bot credentials is still pending; backend runtime is now per-user but only fake-client lifecycle was tested locally.
- Factor computation/value storage is still global by factor name; private custom factors are now excluded from shared precompute/effectiveness storage, but a dedicated per-user factor value schema is still needed if private custom factors should be precomputed instead of computed on demand.
