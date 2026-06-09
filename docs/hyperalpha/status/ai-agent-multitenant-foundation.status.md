# AI Agent Multi-Tenant Foundation Status

Date: 2026-06-09
Branch: `codex/ai-agent-multitenant-foundation`

## Current Status

Status: Local V1 Browser Acceptance Complete / Remote Push Deferred

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
- Admin-only AI runtime visibility shows dispatch queue stale-claim timeout for worker recovery operations.
- AI stream tasks persist runner id and heartbeat timestamps to support future distributed worker routing or takeover.
- AI stream dispatch queue records serializable worker jobs with claim/running/completed/failed states for distributed worker routing.
- AI stream dispatch workers can claim registered task types and run Hyper AI chat/onboarding plus Prompt/Signal/Program/Attribution AI chat jobs from serialized payloads when enabled.
- AI stream dispatch queue recovers stale claimed jobs by requeueing when attempts remain or failing the stream task when attempts are exhausted.
- Hyper AI and Program AI task admission is conversation-scoped, so one conversation cannot run overlapping writes while other users/conversations can still run.
- Context compression memory extraction stores long-term memories under the current user.
- Hyper AI memory categories now include AI Trading-specific strategy, risk, performance, and execution memories for safer long-term context reuse.
- Development compressed memory now has a `docs/hyperalpha/memory/latest.md` pointer for continuation handoff.
- User-scoped Hyperliquid/Binance symbol watchlists, with shared data collectors reading the aggregate symbol union.
- Hyper AI exposes a Hyperliquid AI Trading focus strip using the user's watchlist, then AI Trading Crypto/HIP-3 market-universe presets, then available-symbol fallback to prefill safe strategy prompts.
- Hyper AI AI Trading market selector separates AI Trading market-universe symbols into All, Crypto, and HIP-3 groups so To C users can see both high-volume crypto and HIP-3 stock/index symbols such as `xyz:NVDA`, `xyz:AAPL`, and `xyz:TSLA`.
- Hyper AI AI Trading critical user actions now use a bounded timeout/recovery wrapper so draft/save/approve/adjust/backtest/signal/handoff/reject requests cannot leave buttons permanently stuck after network or dev-server interruptions.
- Hyper AI AI Trading current strategy card now has inline Backtest ID and Metrics JSON controls for attaching external/backtest-service evidence without browser-native prompts; recent spec rows keep the prompt shortcut for compatibility.
- Local LaunchAgent backend now supports `HYPERALPHA_LOCAL_DEV_LIGHT_MODE=true`, skipping heavy background market/news/account collectors for stable local AI Trading/browser acceptance while preserving normal production startup behavior by default.
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
- `/app/ai-trading` and `#ai-trading` route aliases resolve to the existing Hyper AI trading agent page.
- Hyper AI startup splash has a bounded fallback so backend/API startup failures surface the app shell instead of trapping users on the loading screen.
- AI Trading strategy-spec API drafts and validates structured, signal-only Hyperliquid strategy plans with explicit risk, TP/SL, user-approval, and no-direct-order boundaries.
- AI Trading market-universe API exposes Hyperliquid Crypto Top 20/50 and HIP-3 Top 20/50 presets with dex, exchange symbol, category, volume, open interest, leverage, isolated-only, and source metadata.
- AI Trading strategy specs and signal candidates preserve HIP-3 market identity with internal symbol, dex, exchange symbol such as `xyz:NVDA`, display symbol, and category metadata.
- AI Trading strategy specs and signal candidates persist non-secret AI model context (`provider`, `model`, `source`) for DeepSeek/Qwen audit attribution, while validation rejects API key/token/secret fields inside `ai_model`.
- AI Trading strategy specs can attach current-user backtest summaries, and signal handoff eligibility now blocks order-backend handoff until a passing/accepted backtest summary is present in the immutable signal candidate.
- AI Trading backtest handoff evidence now requires parseable quality metrics: positive trade count, max drawdown, and at least one performance metric before a signal event can become handoff-ready.
- AI Trading strategy specs can link current-user Program BacktestResult records as handoff evidence, with owner guards across account/program binding and automatic metrics mapping instead of manual metric entry.
- AI Trading exposes a current-user Program BacktestResult candidate list so users can discover recent completed backtests without knowing raw IDs, while responses omit program code and trading credentials.
- AI Trading strategy specs can auto-link the newest current-user, symbol-matching, handoff-ready Program BacktestResult without accepting unrelated symbols or weak metrics.
- AI Trading strategy specs can build a non-executing Program Backtest preflight for current-user Hyperliquid bindings, recommending a symbol-matching binding and default `/api/programs/backtest` request without starting a backtest or placing orders.
- Hyper AI AI Trading panel shows current strategy backtest-gate status and can attach an external/backtest-service summary to the saved strategy spec without running orders.
- Hyper AI AI Trading panel can attach an existing Program Backtest result ID to a saved strategy spec and load the mapped evidence into chat for review without running orders.
- Hyper AI AI Trading panel lists recent completed Program Backtests with symbols and key metrics, and can attach a listed result to the current strategy spec without manual ID entry.
- Hyper AI AI Trading panel can attach the latest matching Program Backtest evidence from a strategy spec card without manual ID entry.
- AI Trading can return a current-user attached Program Backtest evidence detail packet with metrics, equity-curve sample, trigger/action summaries, and leakage guards without returning Program code, decision snapshots, or credentials.
- AI Trading Program Backtest evidence detail strips sensitive keys from attached summary, evidence summary, and returned config views before returning data.
- Hyper AI AI Trading panel can load a Program Backtest preflight into chat from strategy cards and recent spec rows via a shield action.
- Hyper AI AI Trading panel can run the preflighted current-user Program Backtest SSE flow, then auto-attach the completed Program BacktestResult as strategy evidence without touching the order gateway.
- Hyper AI AI Trading panel can load attached Program Backtest evidence detail into chat for agent review without starting a backtest, attaching new evidence, or submitting orders.
- Hyper AI AI Trading panel renders a compact attached-backtest evidence panel with handoff state, return, drawdown, trade count, action distribution, quality issues, and the first trigger summaries after evidence inspection.
- Hyper AI AI Trading panel can open an expanded attached-backtest evidence dialog with metric cards, an equity-curve sample, action distribution bars, quality issues, and a trigger review table.
- AI Trading has a deep-linkable full-page attached-backtest result route at `/app/ai-trading/backtests/{strategy_spec_id}` and `#ai-trading?backtestSpecId={strategy_spec_id}`, loading current-user evidence detail in read-only mode.
- Hyper AI AI Trading panel can request a per-symbol structured strategy draft and load it into chat for agent review before persistence or execution.
- AI Trading strategy specs can be saved, listed, inspected, approved, and archived per user; approval reruns validation and never emits orders.
- AI Trading strategy specs can be adjusted from natural-language instructions through constrained backend patching; adjustments preserve signal-only/no-direct-order boundaries, invalidate prior approval/backtest evidence, and require re-approval plus fresh handoff-ready backtest evidence before new signals.
- AI Trading strategy specs can also be adjusted through the current user's DeepSeek/Qwen Hyper AI profile: the model returns a constrained JSON adjustment suggestion, then the same safe parser/validation/backtest invalidation path applies before any persistence or signal generation.
- Hyper AI AI Trading strategy draft summary includes save and approval controls backed by the user-scoped strategy-spec API.
- Hyper AI AI Trading strategy draft summary includes a compact natural-language adjustment control that calls the constrained adjustment API for saved or unsaved specs, then reloads the adjusted spec into chat for review.
- Hyper AI AI Trading strategy draft summary includes a DeepSeek/Qwen model-adjust button when the user profile has a supported provider configured; model responses are shown as non-secret `model_context` and `model_suggestion` review packets.
- Approved AI Trading strategy specs can produce a non-executable signal preview candidate with `not_an_order`, no direct AI order placement, and backend-handoff eligibility metadata.
- AI Trading signal preview responses recursively redact sensitive keys before returning data, matching persisted signal-event response boundaries.
- Hyper AI can load approved strategy signal previews into chat for review without submitting them to an execution gateway.
- AI Trading signal candidates are persisted as current-user audit events with review status, handoff status, and full signal JSON before any future execution gateway integration.
- AI Trading signal event detail responses and gateway payloads recursively redact sensitive keys from signal JSON before returning or submitting data.
- AI Trading strategy spec detail/save/approval responses recursively redact sensitive keys from spec JSON before returning data, while preserving original audit JSON in the database.
- Hyper AI signal preview action now creates an auditable signal event and sends the event payload into chat for review.
- Hyper AI signal preview control now stays gated until the approved strategy spec also has handoff-ready backtest evidence, matching the user-facing safety path before signal-event creation.
- AI Trading signal handoff endpoint is present but disabled by default; it only submits audited signal events to a configured external order-backend URL when explicitly enabled.
- AI Trading signal gateway payload now has a documented V1 HTTP JSON contract with stable top-level fields for contract/version, event/spec/user IDs, venue, market identity, action, idempotency, signal age, user confirmation, risk, backtest evidence, validation, execution boundary, and a redacted full signal copy.
- AI Trading includes a local mock signal gateway at `backend/dev_ai_trading_signal_gateway.py` for browser/local handoff acceptance without touching the real order backend.
- AI Trading signal handoff endpoint requires an explicit `confirmed_by_user=true` request before any eligible signal can be submitted to the order backend.
- AI Trading signal handoff eligibility now requires the persisted signal execution boundary to keep `requires_user_confirmation=true` before any order-backend handoff.
- AI Trading signal handoff eligibility now requires the persisted signal execution boundary to keep `signal_only=true` before any order-backend handoff.
- AI Trading signal handoff eligibility now requires persisted signals to keep the expected signal version, review-candidate type, and Hyperliquid venue before any order-backend handoff.
- AI Trading signal handoff eligibility now requires persisted signal action to be tradeable and match the audit event action, and signal symbol to match the audit event symbol.
- AI Trading signal handoff eligibility blocks stale signal events by default after `AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS` so old market signals cannot be submitted silently.
- AI Trading signal gateway environment variables are documented in root and backend `.env.example` templates.
- AI Trading production handoff readiness checker is available at `backend/scripts/ai_trading_production_handoff_check.py`; it refuses disabled, placeholder, localhost/private, mock, non-HTTPS, query/credential-embedded, tokenless, over-timeout, over-age, or unapproved production handoff config without printing token values.
- AI Trading runtime handoff eligibility now enforces the production handoff approval boundary for external order-backend URLs and blocks them with `production_handoff_approval_required` unless `AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true`; local mock gateway URLs remain allowed for local acceptance.
- AI Trading runtime status exposes non-sensitive gateway readiness plus current-user strategy spec and signal event counts.
- AI Trading runtime status exposes the non-secret signal max handoff age so operators can see the stale-signal gate currently enforced by the backend.
- AI Trading runtime status exposes a non-secret gateway `target_kind` (`disabled_or_unconfigured`, `local_mock`, or `external_order_backend`) so local acceptance and UI can distinguish mock handoff from real order-backend handoff without leaking URLs or tokens.
- Hyper AI AI Trading Gateway card now treats runtime `default_handoff_status` and `runtime_config_blockers` as authoritative, so production handoff blockers show as yellow disabled state with readable labels instead of a misleading green enabled URL state.
- Hyper AI AI Trading Gateway card now displays the non-secret gateway target label, including `Local mock` for local acceptance.
- Hyper AI AI Trading panel displays gateway/spec/signal runtime counts when the backend is available.
- Hyper AI AI Trading panel lists recent strategy specs and signal events, and can load saved records into chat for audit review without submitting orders.
- Hyper AI AI Trading panel exposes a gated signal-event handoff control that stays disabled until the backend reports an enabled/configured gateway and only targets unsubmitted `review_candidate` events.
- Hyper AI AI Trading signal-event handoff asks for explicit user confirmation before submitting an eligible signal to the order backend.
- AI Trading signal-event API responses include non-secret `handoff_eligibility` blockers so the frontend and backend share the same handoff preflight decision.
- AI Trading runtime status summarizes review-candidate handoff readiness counts so operators can see ready versus blocked signal events without reading secrets.
- AI Trading runtime status summarizes strategy-spec backtest evidence readiness counts so operators can see ready, blocked, missing, and blocker categories without reading full specs.
- AI Trading signal handoff attempts are persisted as non-secret per-user audit records for blocked, failed, and submitted handoff attempts.
- AI Trading signal handoff attempt responses recursively redact sensitive keys from blockers and eligibility audit JSON before returning data.
- AI Trading signal handoff attempt audit records include non-secret user-confirmation metadata for confirmed blocked, failed, and submitted handoff attempts.
- Submitted and failed AI Trading signal handoff attempts include only a non-secret gateway response summary: HTTP status code plus whitelisted JSON fields such as accepted/status/idempotency/request/code; gateway URL/token, authorization, response body, and arbitrary downstream fields are not stored in public attempt responses.
- Failed AI Trading signal handoff attempts and signal-event errors store sanitized gateway failure summaries instead of raw exception strings, avoiding gateway URL/token/body leakage.
- Hyper AI AI Trading panel can load signal handoff attempt history into chat for audit review without triggering execution.
- AI Trading signal events can be explicitly rejected by the user before handoff; rejection updates the persisted signal review state and makes the event ineligible for backend handoff.
- Persisted AI Trading signal events rewrite signal payload idempotency keys to event-scoped values so multiple candidates from one strategy spec do not collide at handoff.
- Hyper AI recent signal rows show readable Ready/Blocked/Rejected/Submitted status badges plus the first blocker reason when handoff is blocked.
- Hyper AI recent signal rows translate common handoff blocker codes into readable safety messages, including stale signal age versus max-age.
- AI Trading route regression now covers two-user isolation for strategy specs, signal events, signal previews, rejection, handoff, and handoff-attempt audit reads.
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
- V1 acceptance checklist is saved in `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md` to prevent open-ended development and define the exact local/test acceptance gate.
- V1 API-level acceptance runner is saved in `backend/scripts/ai_trading_v1_acceptance_smoke.py`; it uses TestClient, temporary SQLite, a mocked Qwen adjustment response, and a mocked order-backend handoff to prove the strategy/backtest/signal/reject/handoff flow without live Postgres/browser state.
- V1 local environment readiness checker is saved in `backend/scripts/ai_trading_v1_env_check.py`; it reports frontend/backend/Postgres/Docker/mock-gateway readiness, parses the non-secret backend runtime gateway summary, and blocks local V1 acceptance unless gateway `target_kind=local_mock` with no runtime config blockers.
- V1 live-stack acceptance runner is saved in `backend/scripts/ai_trading_v1_live_stack_acceptance.py`; it targets only local URLs by default, requires `--confirm-local-mock-handoff`, verifies the local mock gateway health identity and runtime `target_kind=local_mock`, then proves draft/save/backtest/approve/eligible-signal/confirmed-mock-handoff/attempt-audit/runtime against the running LaunchAgent stack.
- V1 local acceptance aggregate runner is saved in `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh`; it requires `--confirm-local-mock-handoff` and runs backend compile, AI Trading regression, API smoke, default production-gate blocker check, frontend build, runtime readiness, and live local mock handoff in one gate.
- Production handoff readiness checker is saved in `backend/scripts/ai_trading_production_handoff_check.py`; it is a no-network, no-submit gate for live order-backend acceptance and requires `AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true` plus a real HTTPS non-local/non-mock gateway URL and token.
- Final local Browser acceptance completed on 2026-06-09: BTC strategy draft, natural-language adjustment, save, approval, inline backtest evidence, handoff-ready signal preview, rejection, submitted mock handoff visibility, and handoff-attempt audit were verified through `/app/ai-trading`.
- Final local live mock handoff completed on 2026-06-09 against the LaunchAgent stack: spec `#6`, signal event `#4`, `handoff_status=submitted`, latest attempt `submitted`, `gateway_ready=true`.
- Repeatable local live-stack mock handoff completed on 2026-06-09 using `ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff`: latest evidence spec `#13`, signal event `#11`, gateway response summary `status=mock_accepted`, latest attempt `submitted`, runtime `target_kind=local_mock`.
- AI Trading strategy/spec/signal/gateway flow now has a pytest regression covering draft, save, approval, signal-event audit, disabled gateway, enabled handoff, and runtime counts.
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
| AI stream runtime env templates | Done | Root and backend `.env.example` include worker, runner id, local admission, persistence, Redis URL, lease TTL, key prefix, fail-open, and ranked-symbol cache settings |
| AI stream task ID entropy | Done | `generate_task_id()` keeps the readable prefix/timestamp and adds UUID entropy to prevent same-thread same-millisecond collisions |
| AI runtime admin visibility | Done | Admin-only `/api/ai-stream/admin/runtime` plus Settings AI Runtime section expose shared capacity, queue depth, and per-user task occupancy without message/tool payloads |
| AI runtime distributed-admission visibility | Done | Admin runtime stats and Settings AI Runtime display show distributed admission enablement, availability, Redis leases, and lease TTL without exposing Redis URL |
| AI runtime remote-task visibility | Done | Admin runtime stats and Settings AI Runtime display local/effective/remote running counts plus persisted/stale DB running tasks for multi-instance operations |
| AI stream runner heartbeat | Done | `ai_stream_tasks.runner_id` and `last_heartbeat_epoch` record the backend instance and last persisted activity for each AI stream task |
| AI stream dispatch queue foundation | Done | `ai_stream_dispatch_jobs` plus enqueue/claim/running/complete/fail service methods persist serializable worker jobs and expose admin queue stats |
| AI stream dispatch worker handlers | Done | Optional dispatch worker loop claims supported DB jobs; Hyper AI chat/onboarding plus Prompt/Signal/Program/Attribution chat routes register serializable handlers and enqueue instead of running local closures when enabled |
| AI stream stale claim recovery | Done | `AI_STREAM_DISPATCH_CLAIM_STALE_SECONDS` controls recovery of claimed-but-not-running jobs; exhausted jobs mark both dispatch and stream task failed |
| AI runtime stale-claim visibility | Done | Settings AI Runtime displays the dispatch queue claim timeout beside queue state counts |
| Conversation task admission | Done | Hyper AI and Program AI return `already_running` for the same user's active conversation task while allowing other users/conversations to start under capacity limits |
| Compression memory ownership | Done | `compress_messages(..., user_id=...)` propagates current user into background memory extraction |
| AI Trading memory categories | Done | Hyper AI memory service, tool schema, and system prompt support `strategy_memory`, `risk_memory`, `performance_memory`, and `execution_memory` while retaining user scoping |
| Development memory pointer | Done | `docs/hyperalpha/memory/latest.md` points to the latest compressed development memory summary |
| Symbol watchlist ownership | Done | `add_user_symbol_watchlists.py`; Hyperliquid/Binance watchlists are stored per user, with aggregate reads for collectors |
| Watchlist API/AI tool scoping | Done | `/symbols/watchlist` GET/PUT and Hyper AI `get_watchlist/update_watchlist` pass current `user_id` |
| Hyperliquid ranked symbols API | Done | `/api/hyperliquid/symbols/ranked` reads public Hyperliquid `metaAndAssetCtxs`, ranks by 24h notional volume, caches briefly, and falls back to cached available symbols |
| Market universe symbol source | Done | `/api/ai-trading/market-universe` returns Crypto Top 20/50 and HIP-3 Top 20/50 presets for Hyperliquid with non-secret market metadata and delisted-market filtering |
| Hyper AI trading focus UI | Done | Hyper AI config panel loads the current user's Hyperliquid watchlist, falls back to AI Trading Crypto/HIP-3 market-universe presets then available symbols, separates market-universe symbols into All/Crypto/HIP-3 segments, and pre-fills no-auto-order strategy prompts per symbol |
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
| AI Trading route alias | Done | `/app/ai-trading`, `/ai-trading`, and `#ai-trading` resolve to the Hyper AI page without duplicating UI state |
| Hyper AI startup fallback | Done | Splash completes after a bounded wait even if initial backend data is unavailable, allowing the AI Trading shell to render API/connectivity errors |
| AI Trading market universe API | Done | `/api/ai-trading/market-universe` exposes `crypto_top_20`, `crypto_top_50`, `hip3_top_20`, and `hip3_top_50` presets for the To C market selector |
| AI Trading HIP-3 market identity | Done | Strategy drafts and signal candidates keep `market.dex`, `market.exchange_symbol`, `market.display_symbol`, and category metadata so `xyz:NVDA` is not flattened before order-backend handoff |
| AI Trading model context audit | Done | Strategy drafts accept current Hyper AI `llm_provider/llm_model`, store only non-secret `ai_model` fields, warn on missing/non-V1 providers, and mark embedded secrets invalid before approval or signal handoff |
| AI Trading backtest handoff gate | Done | `/api/ai-trading/strategy-specs/{id}/backtest-summary` stores non-executable backtest evidence, and signal-event handoff eligibility blocks candidates without accepted passing backtest evidence |
| AI Trading backtest metrics gate | Done | Handoff readiness requires positive `trade_count`, parseable `max_drawdown`, and at least one performance metric such as `total_return`, `sharpe`, `win_rate`, or `profit_factor` |
| AI Trading Program Backtest bridge | Done | `/api/ai-trading/strategy-specs/{id}/backtest-result` attaches current-user Program BacktestResult evidence via account/program owner guards and maps persisted metrics into the AI Trading backtest gate |
| AI Trading Program Backtest evidence list | Done | `/api/ai-trading/backtest-results` lists current-user completed Program BacktestResult candidates with symbol/status/limit filters, key metrics, and no strategy code or credentials |
| AI Trading latest backtest evidence attach | Done | `/api/ai-trading/strategy-specs/{id}/backtest-result/latest` auto-links the newest current-user, same-symbol, handoff-ready Program BacktestResult and rejects missing/weak/mismatched evidence |
| AI Trading Program Backtest evidence detail | Done | `/api/ai-trading/strategy-specs/{id}/backtest-evidence` returns attached current-user Program Backtest metrics, sampled equity curve, trigger/action summaries, markers, and leakage guards without Program code, full decision snapshots, or credentials |
| AI Trading Program Backtest evidence detail redaction | Done | Attached summary, evidence summary, and returned config views strip sensitive keys such as API keys, access tokens, and private keys |
| AI Trading Program Backtest preflight | Done | `/api/ai-trading/strategy-specs/{id}/backtest-preflight` inspects current-user Hyperliquid account-program bindings, signal pools, and strategy symbol, then returns blockers or a default `/api/programs/backtest` request without executing it |
| AI Trading backtest summary UI | Done | Hyper AI strategy cards display backtest readiness and expose a chart-icon action to attach an external backtest summary JSON to a saved strategy spec |
| AI Trading Program Backtest UI bridge | Done | Hyper AI strategy cards and recent spec rows expose a link-icon action to attach an existing Program Backtest result ID without manual metric entry |
| AI Trading Program Backtest evidence UI | Done | Hyper AI AI Trading panel lists recent Program Backtests and can attach a listed handoff-ready result to the current strategy spec |
| AI Trading latest backtest evidence UI | Done | Hyper AI strategy cards and recent spec rows expose a history-icon action to attach the latest same-symbol handoff-ready Program Backtest evidence |
| AI Trading Program Backtest preflight UI | Done | Hyper AI strategy cards and recent spec rows expose a shield-icon action to save the draft if needed, request preflight, and load the non-executing recommendation into chat |
| AI Trading Program Backtest run UI | Done | Hyper AI strategy cards and recent spec rows expose a run action that requests preflight, asks for user confirmation, streams `/api/programs/backtest`, then attaches the completed Program BacktestResult as non-order evidence |
| AI Trading Program Backtest evidence detail UI | Done | Hyper AI strategy cards and recent spec rows expose a read-only inspect action that loads attached evidence detail into chat for agent review |
| AI Trading compact evidence review panel | Done | Hyper AI renders inspected attached-backtest evidence as a compact metric/action/trigger panel so users can review results without parsing raw JSON |
| AI Trading expanded evidence dialog | Done | Hyper AI opens inspected attached-backtest evidence in a large read-only dialog with metric cards, equity sample chart, action distribution, quality issues, and trigger table |
| AI Trading full-page backtest result route | Done | `/app/ai-trading/backtests/{strategy_spec_id}` and `#ai-trading?backtestSpecId={strategy_spec_id}` resolve to a read-only evidence result page with metrics, equity curve, action distribution, quality issues, and trigger table |
| AI Trading strategy spec API | Done | `/api/ai-trading/strategy-spec/schema|draft|validate` provides a structured, signal-only strategy contract and rejects direct AI order-placement boundaries |
| AI Trading strategy spec UI | Done | Hyper AI AI Trading symbol controls can request a strategy spec draft and load the JSON into chat for review |
| AI Trading strategy spec persistence | Done | `ai_trading_strategy_specs` stores current-user draft/review/approved records; approval reruns validation and archived records are hidden from default lists |
| AI Trading strategy spec approval UI | Done | Hyper AI strategy draft summaries expose save and approve controls without connecting to order execution |
| AI Trading signal preview API | Done | Approved specs can build `hyperalpha.ai_trading.signal_candidate.v1` review candidates; unapproved specs are rejected and previews are marked `not_an_order` |
| AI Trading signal preview response redaction | Done | Direct signal-preview responses recursively mask sensitive keys before returning candidates to clients |
| AI Trading signal preview UI | Done | Hyper AI approved strategy draft summaries can load signal previews into chat for review without submitting to order execution |
| AI Trading signal event audit | Done | `ai_trading_signal_events` stores current-user review candidates with signal JSON and `not_submitted` handoff state |
| AI Trading signal payload redaction | Done | Signal detail responses and gateway payloads recursively mask sensitive keys such as API keys, tokens, secrets, passwords, and private keys |
| AI Trading strategy spec payload redaction | Done | Strategy spec save/detail/approval responses recursively mask sensitive keys while preserving database audit JSON |
| AI Trading audited signal preview UI | Done | Hyper AI signal preview control creates a signal event record before loading the candidate JSON into chat |
| AI Trading signal preview backtest UI gate | Done | Hyper AI disables signal preview until an approved strategy has handoff-ready backtest evidence and shows the same blocker message in the strategy card |
| AI Trading signal gateway boundary | Done | `/api/ai-trading/signal-events/{id}/handoff` defaults to 409 disabled; when configured it submits only audited `not_an_order` events to the external order backend |
| AI Trading handoff confirmation API gate | Done | `/api/ai-trading/signal-events/{id}/handoff` requires `confirmed_by_user=true` before gateway eligibility, gateway POST, or handoff-attempt audit writes |
| AI Trading user-confirmation handoff boundary | Done | Handoff eligibility blocks persisted signals whose execution boundary no longer has `requires_user_confirmation=true`, and the frontend labels the blocker |
| AI Trading signal-only handoff boundary | Done | Handoff eligibility blocks persisted signals whose execution boundary no longer has `signal_only=true`, and the frontend labels the blocker |
| AI Trading signal identity handoff boundary | Done | Handoff eligibility blocks persisted signals whose version, candidate type, or venue no longer matches the AI Trading Hyperliquid review-signal contract |
| AI Trading event/signal consistency boundary | Done | Handoff eligibility blocks non-tradeable signal actions plus action/symbol mismatches between the audit event and nested signal payload |
| AI Trading stale signal handoff gate | Done | Handoff eligibility blocks signal events older than `AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS` and includes non-secret signal age/max-age metadata in preflight responses |
| AI Trading signal gateway env templates | Done | Root and backend `.env.example` document gateway enablement, URL, timeout, and bearer token without exposing secrets to the AI model |
| AI Trading production handoff readiness gate | Done | `backend/scripts/ai_trading_production_handoff_check.py` checks live gateway config without network calls or token output, and runtime handoff eligibility blocks external order-backend URLs unless production handoff is explicitly approved |
| AI Trading runtime visibility | Done | `/api/ai-trading/runtime` exposes gateway enablement/readiness and current-user strategy spec/signal event counts without URL/token leakage |
| AI Trading runtime handoff age visibility | Done | Runtime gateway status includes `max_handoff_age_seconds`, and Hyper AI shows the compact max-age value in the Gateway card |
| AI Trading runtime panel | Done | Hyper AI AI Trading panel displays gateway/spec/signal totals, uses runtime gateway blockers for the Gateway card state, and refreshes after draft save, approval, and signal event creation |
| AI Trading recent records panel | Done | Hyper AI AI Trading panel lists recent saved specs/signal events and lets users inspect them into chat for audit review |
| AI Trading signal handoff UI | Done | Recent signal events expose a disabled-by-default, gateway-gated handoff button for unsubmitted `review_candidate` events |
| AI Trading signal handoff confirmation | Done | Eligible recent signal handoff requires an explicit confirmation dialog before POSTing to the order backend |
| AI Trading handoff preflight | Done | Signal event list/detail/submit share non-secret `handoff_eligibility` blockers for gateway readiness, event state, and signal-only boundaries |
| AI Trading handoff runtime summary | Done | Runtime status includes review-candidate handoff readiness counts and blocker counts; Hyper AI panel shows total signals versus ready candidates |
| AI Trading strategy backtest runtime summary | Done | Runtime status includes strategy-spec backtest evidence ready/blocked/missing counts and blocker counts; Hyper AI panel shows total specs versus backtest-ready specs |
| AI Trading handoff attempt audit | Done | `ai_trading_signal_handoff_attempts` stores blocked/failed/submitted handoff attempts without gateway URL/token or trading credentials |
| AI Trading handoff attempt response redaction | Done | Handoff-attempt blockers and eligibility audit JSON recursively mask sensitive keys before API responses |
| AI Trading handoff confirmation audit | Done | Confirmed handoff attempts persist non-secret `user_confirmation` metadata inside eligibility audit JSON, while unconfirmed handoff requests still write no attempt |
| AI Trading handoff gateway response audit | Done | Submitted handoff attempts persist only non-secret gateway response status metadata inside eligibility audit JSON |
| AI Trading failed handoff error sanitization | Done | Failed handoff event/attempt errors persist sanitized error type/status summaries and never raw gateway exception text |
| AI Trading handoff attempt UI | Done | Recent signal events expose a read-only handoff history button that loads non-secret attempts into chat for audit review |
| AI Trading signal rejection | Done | Review candidate signal events can be rejected before handoff; rejected events store review reason, become ineligible, and are visible in runtime status |
| AI Trading signal idempotency | Done | Persisted signal events carry event-scoped `signal_event:{id}` idempotency keys, and gateway payloads reuse the same key |
| AI Trading signal status UI | Done | Recent signal rows display readable handoff/review status badges and first-blocker summaries for blocked candidates |
| AI Trading handoff blocker labels | Done | Recent signal rows and handoff tooltips translate common blocker codes into readable safety labels, including stale signal age/max-age |
| AI Trading API regression test | Done | `backend/tests/test_ai_trading_routes.py` covers strategy draft/save/approve, signal event creation, disabled/enabled handoff, and runtime counts with SQLite |
| AI Trading user isolation regression | Done | `backend/tests/test_ai_trading_routes.py` now creates Alice/Bob clients on one SQLite DB and verifies Bob cannot list/read/approve/archive/preview/create/reject/handoff Alice's records or attempts |
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
- Passed: AI stream runner heartbeat smoke test in `uv run`: task create/chunk/complete persisted `runner_id` and refreshed `last_heartbeat_epoch`; admin runtime stats returned the current runner id.
- Passed: AI stream dispatch queue foundation smoke test in `uv run`: dispatch jobs enqueued, duplicate enqueue stayed idempotent, type-scoped claim worked, running/completed/failed transitions persisted runner/error state, and admin runtime stats exposed queue counts.
- Passed: AI stream dispatch worker fake-handler smoke test in `uv run`: a claimed job was adopted by the runner, emitted chunks through the shared stream buffer, completed the task, and persisted completed dispatch/task runner state.
- Passed: Hyper AI dispatch enqueue smoke test in `uv run`: chat and onboarding task starts created stream tasks and pending dispatch jobs with serialized payloads when dispatch mode was enabled.
- Passed: Prompt/Signal/Program/Attribution dispatch route compile in both system Python and `uv run` backend environment; static AST check confirmed `prompt_ai.chat`, `signal_ai.chat`, `program_ai.chat`, and `attribution_ai.chat` task types plus `register_ai_stream_task_handler` calls.
- Passed: AI stream error-message extraction smoke test in `uv run`: `message`, `content`, `error`, `text`, `raw`, non-dict payloads, and empty payload fallbacks produce readable task failure reasons.
- Passed: AI stream dispatch stale-claim recovery smoke test in `uv run` with SQLite: stale claimed jobs fail the stream task when attempts are exhausted and are re-claimed when attempts remain.
- Passed: Frontend production build after Settings AI Runtime displayed dispatch queue claim timeout.
- Warning only: Live handler registry import check was blocked by local PostgreSQL being stopped because `analytics_routes.py` imports snapshot DB connection at module import time; compile and static checks passed.
- Passed: Frontend production build after Settings AI Runtime displayed dispatch queue pending/claimed/running/completed/failed counts.
- Passed: Hyperliquid ranked symbols API smoke test in `uv run`: fake `metaAndAssetCtxs` data sorted by `dayNtlVlm`, skipped delisted symbols, parsed market fields, and reused the in-process cache.
- Passed: Hyper AI trading focus UI frontend build after switching the no-auto-order prompt strip to watchlist -> 24h volume-ranked -> available-symbol fallback.
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
- Passed: Development compressed memory summary updated for 2026-06-09 with AI stream dispatch, worker, stale-claim, verification, and blocked push state.
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
- Passed: Frontend production build after adding `/app/ai-trading` and `#ai-trading` aliases.
- Partial: Playwright opened the current repo Vite app at `http://127.0.0.1:5174/app/ai-trading` and confirmed the app title/root rendered; backend API/WS calls returned errors because the local backend/Postgres were not running.
- Passed: Frontend production build after adding a bounded Hyper AI startup splash fallback.
- Passed: Playwright opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the fallback window, and confirmed the Hyper AI app shell rendered instead of remaining stuck on splash while backend API/WS calls failed locally.
- Passed: AI Trading strategy spec compile in both system Python and `uv run` backend environment for the service, API route, and main router registration.
- Passed: AI Trading strategy spec service smoke test in `uv run`: complete drafts become `ready_for_review`, missing TP/SL returns `needs_user_input`, invalid owner IDs are flagged, and direct AI order-placement flags are rejected.
- Passed: AI Trading strategy spec FastAPI route smoke test in `uv run`: schema, draft, and validate endpoints preserve `signal_only`, `ai_may_place_orders=false`, and reject direct-order mutation.
- Passed: Frontend production build after adding the Hyper AI AI Trading strategy-spec draft controls.
- Partial: Playwright opened the current repo Vite app at `http://127.0.0.1:5174/app/ai-trading` and confirmed the shell still renders; the new per-symbol draft control could not be clicked in-browser because backend/API symbol loading is unavailable while local backend/Postgres are not running.
- Passed: AI Trading strategy spec persistence compile in both system Python and `uv run` backend environment for ORM model, migration, service, and route changes.
- Passed: AI Trading strategy spec persistence smoke test in `uv run` with SQLite: current-user spec save/list/get/approve/archive flow worked and archived records disappeared from default lists.
- Passed: AI Trading strategy spec HTTP CRUD smoke test in `uv run` with FastAPI TestClient and SQLite: save/list/detail/approve/archive endpoints stayed user-scoped and preserved approval state.
- Passed: Frontend production build after adding Hyper AI strategy spec save/approval controls.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading` and confirmed the shell still renders; full save/approve click acceptance still needs local backend/Postgres and loaded Hyperliquid symbols.
- Passed: AI Trading signal preview compile in both system Python and `uv run` backend environment for service and route changes.
- Passed: AI Trading signal preview HTTP smoke test in `uv run` with FastAPI TestClient and SQLite: unapproved specs returned 400; approved specs produced `not_an_order` signal candidates with `ai_may_place_orders=false`.
- Passed: Frontend production build after adding Hyper AI signal preview controls for approved strategy specs.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading` and confirmed the shell still renders; full signal-preview click acceptance still needs local backend/Postgres and loaded Hyperliquid symbols.
- Passed: AI Trading signal event audit compile in both system Python and `uv run` backend environment for ORM model, migration, service, and route changes.
- Passed: AI Trading signal event HTTP smoke test in `uv run` with FastAPI TestClient and SQLite: unapproved specs cannot create events, approved specs create `review_candidate` events, list/detail stay current-user scoped, and stored signal JSON remains `not_an_order`.
- Passed: Frontend production build after routing Hyper AI signal preview control through the auditable signal-event endpoint.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading` and confirmed the shell still renders; full audited signal event click acceptance still needs local backend/Postgres and loaded Hyperliquid symbols.
- Passed: AI Trading signal handoff compile in both system Python and `uv run` backend environment for service and route changes.
- Passed: AI Trading signal handoff HTTP smoke test in `uv run` with FastAPI TestClient and SQLite: disabled gateway returns 409; monkeypatched enabled gateway submits `AI_TRADING_SIGNAL_CANDIDATE`, sets event `submitted`, stores `handoff_status=submitted`, and sends bearer auth only to the gateway.
- Passed: Root and backend env templates updated with disabled-by-default AI Trading signal gateway settings.
- Passed: AI Trading runtime status compile in both system Python and `uv run` backend environment for service and route changes.
- Passed: AI Trading runtime status HTTP smoke test in `uv run` with FastAPI TestClient and SQLite: empty runtime hides secrets, then approved specs and review signal events appear in current-user counts.
- Passed: Frontend production build after adding the Hyper AI AI Trading gateway/spec/signal runtime status panel.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading` and confirmed the shell still renders; runtime panel data requires local backend/Postgres availability.
- Passed: Frontend production build after adding the Hyper AI AI Trading recent specs/signals audit panel and 500-response runtime fetch guard.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` after the recent records UI work.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; recent-record click acceptance still needs local backend/Postgres and persisted test records.
- Passed: Frontend production build after adding the gateway-gated signal-event handoff button to the recent signals panel.
- Passed: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` after the handoff UI work.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; handoff button click acceptance still needs local backend/Postgres, persisted signal events, and configured gateway readiness.
- Passed: Python syntax compile for AI Trading service/routes after adding signal-event `handoff_eligibility` preflight serialization.
- Passed: AI Trading route regression test after adding handoff preflight assertions for disabled gateway, enabled gateway eligibility, and submitted-event duplicate-blocking.
- Passed: Frontend production build after switching recent signal handoff buttons to backend-provided `handoff_eligibility`.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; preflight UI click acceptance still needs local backend/Postgres and persisted signal events.
- Passed: AI Trading route regression test after adding runtime handoff readiness assertions for disabled, enabled, and submitted-event states.
- Passed: Python syntax compile for AI Trading service/routes after adding runtime handoff readiness summary.
- Passed: Frontend production build after showing signal total/ready counts in the Hyper AI AI Trading runtime panel.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; live runtime ready-count rendering still needs local backend/Postgres.
- Passed: Python syntax compile for AI Trading handoff attempt model, migration, service, and route additions.
- Passed: AI Trading route regression test after adding handoff attempt audit assertions for disabled blocked attempts and enabled submitted attempts, including no gateway token/URL leakage in attempt responses.
- Passed: Frontend production build after adding the read-only handoff-attempt history control to recent signal events.
- Passed: AI Trading route regression test after the handoff-attempt frontend integration.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; handoff history click acceptance still needs local backend/Postgres and persisted signal events.
- Passed: Python syntax compile for AI Trading service/routes after adding signal-event rejection.
- Passed: AI Trading route regression test after adding rejected-event assertions and ensuring rejected events cannot hand off.
- Passed: Frontend production build after adding the recent signal reject control.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; reject button click acceptance still needs local backend/Postgres and persisted signal events.
- Passed: AI Trading route regression test after asserting persisted signal events use event-scoped idempotency keys and gateway payloads reuse the same key.
- Passed: Frontend production build after adding readable Ready/Blocked/Rejected/Submitted badges and first-blocker summaries to recent signal rows.
- Passed: AI Trading route regression test after the recent signal status UI change.
- Partial: Playwright re-opened `http://127.0.0.1:5174/app/ai-trading`, waited beyond the splash fallback, and confirmed the Hyper AI / AI Trading shell rendered; live signal badge rendering still needs local backend/Postgres and persisted signal events.
- Passed: Hyper AI memory trading-category compile in both system Python and `uv run` backend environment for memory service and tool schema.
- Passed: Hyper AI memory trading-category smoke test in `uv run` with SQLite: `strategy_memory`, `risk_memory`, `performance_memory`, and `execution_memory` are accepted categories and user-scoped reads return the expected entries.
- Passed: AI Trading route regression test: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` passed cleanly, covering draft/save/approve, signal event audit, disabled gateway 409, monkeypatched enabled handoff, and runtime counts.
- Passed: AI Trading route multi-user isolation regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` passed with Alice/Bob coverage for strategy specs, signal events, handoff, rejection, and attempt audit reads.
- Passed: AI Trading route/service/test syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading market-universe route regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` passed with fake Hyperliquid core/HIP-3 metadata covering volume sorting, delisted filtering, `xyz:` HIP-3 exchange symbols, and top presets.
- Passed: AI Trading market-universe Python syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after Hyper AI symbol loading switched from generic ranked symbols to AI Trading market-universe presets.
- Passed: AI Trading HIP-3 identity route regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` passed with `xyz:NVDA` draft/save/approve/signal-event coverage and signal payload preserving `exchange_symbol=xyz:NVDA`.
- Passed: AI Trading route/service/test syntax compile after HIP-3 identity preservation.
- Passed: AI Trading model-context regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` passed with DeepSeek/Qwen provider/model persisted into spec/signal and secret fields rejected by validation.
- Passed: Frontend production build after strategy draft requests started passing current Hyper AI provider/model as non-secret model context.
- Passed: AI Trading backtest gate regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` passed with missing-backtest signal events blocked even when gateway is enabled, accepted backtest summaries enabling only newly generated immutable signal events, and Bob unable to attach backtest summaries to Alice specs.
- Passed: AI Trading backtest gate syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the Hyper AI backtest readiness badge and external backtest-summary attach action.
- Passed: AI Trading route regression re-run after the frontend backtest summary integration: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 6 passing tests.
- Passed: AI Trading backtest metrics quality regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 7 passing tests, including weak accepted backtest summaries blocked from gateway handoff.
- Passed: AI Trading backtest metrics syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after syncing Hyper AI backtest ready UI with the backend metrics gate.
- Passed: AI Trading Program Backtest bridge regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 9 passing tests, including owned Program BacktestResult attachment, cross-user backtest-result rejection, and gateway-ready handoff eligibility after linked metrics.
- Passed: AI Trading Program Backtest bridge syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the Hyper AI link-icon Program Backtest result attachment action.
- Passed: AI Trading Program Backtest evidence-list regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 9 passing tests, including current-user list isolation, symbol filtering, handoff-ready calculation, and no API key/program code leakage in list responses.
- Passed: AI Trading Program Backtest evidence-list syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the recent Program Backtests list and direct attach action.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned the Vite app HTML after the Program Backtest evidence-list UI; click-through browser automation remains pending.
- Passed: AI Trading latest matching backtest evidence regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 10 passing tests, including same-symbol selection, weak-metrics skip, and no-match rejection.
- Passed: AI Trading latest matching evidence syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the history-icon latest matching Program Backtest evidence action.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned the Vite app HTML after the latest matching evidence UI; click-through browser automation remains pending.
- Passed: AI Trading Program Backtest preflight regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 12 passing tests, covering owned binding recommendation, symbol mismatch blockers, user isolation, and no code/API-key leakage.
- Passed: AI Trading Program Backtest preflight syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the shield-icon Program Backtest preflight action.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned 200 after the Program Backtest preflight UI; click-through browser automation remains pending.
- Passed: Frontend production build after adding the Program Backtest run action that streams `/api/programs/backtest` and auto-attaches the completed result.
- Passed: AI Trading route regression re-run after Program Backtest run UI: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 12 passing tests.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned 200 after the Program Backtest run UI; in-app Browser navigation to the local URL was blocked by Browser URL policy, so click-through acceptance remains pending.
- Passed: AI Trading Program Backtest evidence-detail regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 13 passing tests, covering current-user evidence detail, trigger/action summaries, cross-user rejection, missing-evidence blocker, and no Program code/API-key/decision snapshot leakage.
- Passed: AI Trading Program Backtest evidence-detail syntax compile: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py services/ai_trading_market_universe_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the read-only attached backtest evidence inspect action.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned 200 after the evidence detail UI; click-through acceptance remains pending because the in-app Browser local URL policy blocked navigation in this session.
- Passed: Frontend production build after rendering the compact attached-backtest evidence review panel.
- Passed: AI Trading route regression re-run after compact evidence panel: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 13 passing tests.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned 200 after the compact evidence panel; click-through browser acceptance remains pending.
- Passed: Frontend production build after adding the expanded attached-backtest evidence dialog.
- Passed: AI Trading route regression re-run after expanded evidence dialog: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 13 passing tests.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned 200 after the expanded evidence dialog; click-through browser acceptance remains pending.
- Passed: Frontend production build after adding the AI Trading full-page attached-backtest result route.
- Passed: AI Trading route regression re-run after the full-page backtest result route: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 13 passing tests.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading/backtests/1` returned 200; authenticated click-through/live evidence acceptance remains pending.
- Passed: AI Trading route regression after strategy backtest runtime summary: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 14 passing tests, covering missing, weak, passing, and cross-user-empty evidence readiness counts.
- Passed: Frontend production build after showing total specs versus backtest-ready specs in the AI Trading runtime panel.
- Passed: Frontend production build after gating Hyper AI signal preview on handoff-ready backtest evidence.
- Passed: AI Trading route regression re-run after the frontend signal-preview gate: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 14 passing tests.
- Passed: Frontend production build after adding explicit signal handoff confirmation before order-backend submission.
- Passed: AI Trading route regression re-run after the handoff confirmation UI: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 14 passing tests.
- Passed: AI Trading route regression after requiring `confirmed_by_user=true` in the handoff API: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 14 passing tests, including no gateway call and no new attempt when confirmation is false.
- Passed: Frontend production build after sending `confirmed_by_user=true` and a confirmation source from the confirmed Hyper AI signal handoff action.
- Passed: AI Trading route regression after adding the stale signal handoff gate: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 15 passing tests, including stale signal eligibility/runtime/blocked-attempt assertions.
- Passed: Frontend production build after documenting the stale signal handoff age gate in env templates.
- Passed: Frontend production build after adding readable Hyper AI handoff blocker labels.
- Passed: AI Trading route regression re-run after readable handoff blocker labels: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 15 passing tests.
- Passed: AI Trading route regression after adding handoff confirmation metadata to attempt audits: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 15 passing tests.
- Passed: AI Trading service/route/test syntax compile after handoff confirmation audit: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after adding non-secret gateway response status to submitted handoff attempts: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 15 passing tests.
- Passed: AI Trading service/route/test syntax compile after gateway response attempt audit: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after sanitizing failed gateway handoff errors: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 16 passing tests, including no gateway URL/token/body leakage in API detail, signal-event error, or failed attempt audit.
- Passed: AI Trading service/route/test syntax compile after failed handoff error sanitization: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after exposing runtime max handoff age: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 16 passing tests.
- Passed: Frontend production build after showing the runtime max handoff age in the Hyper AI Gateway card.
- Passed: AI Trading route regression after recursive signal payload redaction: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 17 passing tests, including sensitive field redaction in signal detail and gateway payloads.
- Passed: AI Trading service/route/test syntax compile after signal payload redaction: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after strategy spec response redaction: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 18 passing tests, including save/detail/approval response redaction while preserving original database audit JSON.
- Passed: AI Trading service/route/test syntax compile after strategy spec response redaction: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after Program Backtest evidence detail redaction: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 18 passing tests, including config-polluted evidence detail responses without sensitive key names or values.
- Passed: AI Trading service/route/test syntax compile after evidence detail redaction: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after handoff attempt response redaction: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 19 passing tests, including polluted blockers/eligibility audit JSON responses without leaking raw secrets.
- Passed: AI Trading service/route/test syntax compile after handoff attempt response redaction: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after signal-preview response redaction: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 20 passing tests, including attached backtest config secrets masked in direct signal preview responses.
- Passed: AI Trading service/route/test syntax compile after signal-preview response redaction: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: AI Trading route regression after enforcing `signal_only` before handoff: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 21 passing tests, including detail/runtime/handoff/attempt blockers when a persisted signal boundary is mutated to `signal_only=false`.
- Passed: AI Trading service/route/test syntax compile after signal-only handoff boundary: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding a readable `signal_only` blocker label in the Hyper AI recent signal panel: `cd frontend && npm run build`. First attempt hit local `spawn sh EAGAIN`; retry passed with existing browserslist/baseline and chunk-size warnings.
- Passed: AI Trading route regression after enforcing `requires_user_confirmation` before handoff: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 22 passing tests, including detail/runtime/handoff/attempt blockers when a persisted signal boundary is mutated to `requires_user_confirmation=false`.
- Passed: AI Trading service/route/test syntax compile after user-confirmation handoff boundary: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding a readable `requires_user_confirmation` blocker label in the Hyper AI recent signal panel: `cd frontend && npm run build`; existing browserslist/baseline and chunk-size warnings remain.
- Passed: AI Trading route regression after enforcing persisted signal identity before handoff: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 23 passing tests, including detail/runtime/handoff/attempt blockers when version, candidate type, and venue are mutated.
- Passed: AI Trading service/route/test syntax compile after signal identity handoff boundary: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding readable signal identity blocker labels in the Hyper AI recent signal panel: `cd frontend && npm run build`; existing browserslist/baseline and chunk-size warnings remain.
- Passed: AI Trading route regression after enforcing event/signal action-symbol consistency before handoff: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 24 passing tests, including detail/runtime/handoff/attempt blockers when nested signal action becomes non-tradeable and action/symbol diverge from the audit event.
- Passed: AI Trading service/route/test syntax compile after event/signal consistency boundary: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding readable event/signal action-symbol blocker labels in the Hyper AI recent signal panel: `cd frontend && npm run build`; existing browserslist/baseline and chunk-size warnings remain.
- Passed: AI Trading signal gateway contract regression after stabilizing the V1 HTTP JSON payload: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 25 passing tests, including `test_ai_trading_signal_gateway_payload_contract_is_stable_signal_only`.
- Passed: AI Trading service/route/test syntax compile after signal gateway contract fields: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Added: `docs/hyperalpha/ai-trading-signal-gateway-contract.md` documents the disabled-by-default gateway config, required payload, handoff gates, downstream order-backend responsibilities, and test evidence.
- Added: `docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md` defines V1 target, required capabilities, current verified evidence, non-accepted items, and final pass criteria.
- Passed: mock signal gateway compile and health check: `cd backend && uv run python -m py_compile dev_ai_trading_signal_gateway.py`, then `uv run uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1` and `curl http://127.0.0.1:5621/health` returned `{"ok":true,...}`; temporary service was stopped.
- Passed: mock signal gateway regression: `cd backend && uv run pytest tests/test_ai_trading_mock_gateway.py -q` returned 2 passing tests, covering valid V1 payload acceptance/audit logging and direct-order boundary rejection.
- Passed: combined AI Trading backend regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py -q` returned 29 passing tests.
- Passed: V1 API-level acceptance smoke: `cd backend && uv run python scripts/ai_trading_v1_acceptance_smoke.py` returned `success=true`, covering draft, Qwen model-adjust bridge, save, handoff-ready backtest summary, approval, rejected signal event, submitted mock-gateway handoff event, handoff attempt audit, runtime summary, and signal-only gateway contract.
- Passed: V1 environment readiness checker compile/run: `cd backend && uv run python -m py_compile scripts/ai_trading_v1_env_check.py` and `cd backend && uv run python scripts/ai_trading_v1_env_check.py` succeeded; after starting Docker Desktop, `docker compose up -d postgres`, mock gateway `5621`, and backend `8802`, current report is `ready=true` for frontend `5174`, backend runtime `8802`, Postgres `5432`, Docker, and mock gateway.
- Passed: AI Trading gateway response-summary regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py -q` returned 29 passing tests, covering submitted/failed handoff attempts with whitelisted response summaries and no response token/body/authorization leakage.
- Passed: AI Trading gateway response-summary syntax compile: `cd backend && uv run python -m py_compile services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py scripts/ai_trading_v1_acceptance_smoke.py`.
- Passed: V1 API-level acceptance smoke after response-summary audit: `cd backend && uv run python scripts/ai_trading_v1_acceptance_smoke.py` returned `success=true`.
- Passed: AI Trading route regression after natural-language strategy adjustment API: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 26 passing tests, including unpersisted adjustment, saved-record adjustment, approval/backtest invalidation, direct-order-intent ignore warning, and cross-user adjust 404.
- Passed: AI Trading service/route/test syntax compile after strategy adjustment API: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the Hyper AI strategy adjustment control: `cd frontend && npm run build`; existing browserslist/baseline and chunk-size warnings remain.
- Passed: AI Trading route regression after DeepSeek/Qwen model-adjust bridge: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 27 passing tests, including a mocked Qwen profile/model response that applies through safe adjustment, invalidates prior approval/backtest, returns non-secret model context/suggestion, and keeps cross-user model-adjust 404.
- Passed: AI Trading service/route/test syntax compile after model-adjust bridge: `cd backend && uv run python -m py_compile api/ai_trading_routes.py services/ai_trading_strategy_spec_service.py tests/test_ai_trading_routes.py`.
- Passed: Frontend production build after adding the DeepSeek/Qwen model-adjust button to the Hyper AI strategy panel: `cd frontend && npm run build`; existing browserslist/baseline and chunk-size warnings remain.
- Partial: Playwright CLI opened `http://127.0.0.1:5174/app/ai-trading` and captured page title `Hyper Alpha Arena`; the page rendered the Hyper AI shell/onboarding state, but console errors showed local backend API/WS failures because the backend was not running.
- Blocked: local backend `uv run uvicorn main:app --port 5611 --host 127.0.0.1` failed during import because local PostgreSQL on `localhost:5432` was not running; `database.snapshot_connection` raised `psycopg2.OperationalError`.
- Blocked: local SQLite fallback probe with `DATABASE_URL=sqlite:///./tmp_hyperalpha_dev.db SNAPSHOT_DATABASE_URL=sqlite:///./tmp_hyperalpha_snapshot.db uv run uvicorn main:app --port 5611 --host 127.0.0.1` produced many Postgres-specific migration/model-validation errors and did not become reliably reachable for AI Trading runtime acceptance; temporary SQLite files were removed.
- Blocked: `docker compose up -d postgres` could not start because Docker daemon was not running (`/Users/mo/.docker/run/docker.sock` missing); local `psql`/`pg_isready` tools were also unavailable.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned the Vite app HTML after the Program Backtest bridge UI; Playwright package was unavailable in current node module resolution, so click-through browser automation remains pending.
- Partial: HTTP shell check for `http://127.0.0.1:5174/app/ai-trading` returned the Vite app HTML after the backtest summary UI change; full click-through attach-summary acceptance still needs browser automation plus local backend/Postgres data.
- Passed: In-app Browser opened `http://127.0.0.1:5174/app/ai-trading`, skipped local onboarding without submitting an API key, and confirmed the Hyper AI / AI Trading page renders with Gateway `available / 15m max`, Specs/Signals runtime counts, All/Crypto/HIP-3 market segments, crypto symbols including BTC/ETH/HYPE, and HIP-3 symbols including `xyz:NVDA`, `xyz:AAPL`, and `xyz:TSLA`.
- Passed: In-app Browser clicked HIP-3 and confirmed the filtered symbol list contains `xyz:NVDA`, `xyz:AAPL`, and `xyz:TSLA` while excluding BTC; clicking `xyz:NVDA` fills a safe AI Trading Agent prompt that asks for strategy analysis, risk constraints, TP/SL review, HOLD when constraints are incomplete, and no direct order placement.
- Passed: In-app Browser clicked the `xyz:NVDA` draft strategy-spec control and, after the local draft API completed, confirmed the UI renders `NVDA · 15m`, `ready_for_review`, `Bias hold`, `Max loss 1%`, `Leverage 3x`, `Boundary signal only`, `Backtest not_run`, and `Unsaved draft`.
- Passed: Frontend production build after adding AI Trading All/Crypto/HIP-3 market segment controls: `cd frontend && npm run build`; existing browserslist/baseline and chunk-size warnings remain.
- Passed: V1 environment checker after switching default backend URL to frontend-compatible `http://127.0.0.1:8802` and adding a browser-compatible `Accept` header: `cd backend && uv run python -m py_compile scripts/ai_trading_v1_env_check.py && uv run python scripts/ai_trading_v1_env_check.py` returned `ready=true`.
- Passed: Local LaunchAgent self-healing is installed as `com.hyperalpha.ai-trading-local`. The installer now syncs a runtime copy to `/Users/mo/Library/Application Support/HyperAlpha/runtime/hyperalpha-ai-trading`, rewrites the runtime editable backend `.pth`, and runs frontend/backend/mock gateway from that copy to avoid macOS Documents background-execution restrictions. After stopping the previous local services and reinstalling, launchd restored frontend `5174`, backend `8802`, and mock gateway `5621`; `cd backend && uv run python scripts/ai_trading_v1_env_check.py` returned `ready=true`.
- Passed: In-app Browser reloaded `http://127.0.0.1:5174/app/ai-trading` after the LaunchAgent runtime copy was active, skipped onboarding without an API key, and confirmed Gateway `available / 15m max`, All/Crypto/HIP-3 segments, and HIP-3 symbols including `xyz:NVDA`, `xyz:AAPL`, and `xyz:TSLA`.
- Passed: repeatable local live-stack acceptance script compile and guard: `cd backend && uv run python -m py_compile scripts/ai_trading_v1_live_stack_acceptance.py` passed, and running it without `--confirm-local-mock-handoff` refused to submit a handoff.
- Passed: repeatable local live-stack mock handoff: `cd backend && uv run python scripts/ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff` returned `success=true` against backend `8802` and mock gateway `5621`, creating latest evidence spec `#8`, signal event `#6`, and a submitted attempt with gateway response summary `status=mock_accepted`.
- Passed: LaunchAgent runtime mirror was resynced after the live-stack acceptance script commit with `scripts/local-dev/install_launch_agent.sh`; immediately after restart backend `8802` was still cold-starting, and a retry after about 10 seconds returned `ready=true` for frontend `5174`, backend `8802`, mock gateway `5621`, Docker, and Postgres `5432`.
- Passed: production handoff readiness checker compile and focused tests: `cd backend && uv run python -m py_compile scripts/ai_trading_production_handoff_check.py tests/test_ai_trading_production_handoff_check.py` and `cd backend && uv run pytest tests/test_ai_trading_production_handoff_check.py -q` returned 5 passing tests.
- Passed: production handoff readiness checker behavior: default `cd backend && uv run python scripts/ai_trading_production_handoff_check.py --strict` correctly returned non-zero with blockers for disabled/missing URL/missing token/missing approval, while a fake HTTPS `orders.hyperalpha.org` config returned `production_handoff_ready=true` and did not print the token value.
- Passed: AI Trading runtime production handoff gate route regression: `cd backend && uv run pytest tests/test_ai_trading_routes.py -q` returned 29 passing tests, including external gateway approval blocking and local mock gateway bypass.
- Passed: combined AI Trading regression with production handoff checker: `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` returned 36 passing tests.
- Passed: V1 API-level acceptance smoke after runtime production gate: `cd backend && uv run python scripts/ai_trading_v1_acceptance_smoke.py` returned `success=true`; local mock gateway still bypasses the production approval flag.
- Passed: local runtime readiness after the production handoff checker slice: `cd backend && uv run python scripts/ai_trading_v1_env_check.py` returned `ready=true`.
- Passed: frontend production build after the production handoff checker docs/env slice: `cd frontend && npm run build`; existing browserslist/baseline/chunk-size warnings remain.
- Passed: LaunchAgent runtime mirror was resynced after commit `e3d561e` with `scripts/local-dev/install_launch_agent.sh`; after a short backend cold start, `cd backend && uv run python scripts/ai_trading_v1_env_check.py` returned `ready=true`.
- Passed: LaunchAgent runtime mirror was resynced after commit `121272f` with `scripts/local-dev/install_launch_agent.sh`; runtime now reports `production_handoff_approved=false`, `runtime_config_blockers=[]`, and local mock gateway `default_handoff_status=available`; `ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff` returned `success=true` with spec `#10`, signal event `#8`, and gateway response `mock_accepted`.
- Passed: frontend production build after Gateway runtime-blocker UI: `cd frontend && npm run build`; existing browserslist/baseline/chunk-size warnings remain.
- Passed: current-source HTTP shell check after Gateway runtime-blocker UI: temporary Vite server on `http://127.0.0.1:5175/app/ai-trading` returned 200. Browser automation was not run because `playwright` is not installed in the repo.
- Passed: AI Trading backend combined regression after Gateway runtime-blocker UI: `cd backend && uv run pytest tests/test_ai_trading_routes.py tests/test_ai_trading_mock_gateway.py tests/test_ai_trading_production_handoff_check.py -q` returned 36 passing tests.
- Passed: LaunchAgent runtime mirror was resynced after commit `3508242` with `scripts/local-dev/install_launch_agent.sh`; after cold start, `cd backend && uv run python scripts/ai_trading_v1_env_check.py` returned `ready=true` and `curl -I http://127.0.0.1:5174/app/ai-trading` returned 200.
- Passed: AI Trading env checker now parses backend runtime JSON, exposes `checks.backend_8802.runtime_gateway`, and blocks local readiness if `target_kind` is not `local_mock` or runtime config blockers are present; `cd backend && uv run pytest tests/test_ai_trading_env_check.py -q` returned 3 passing tests.
- Passed: aggregate AI Trading V1 local acceptance runner: `scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff` completed backend compile, 42 AI Trading regressions, API-level smoke, default production handoff gate blocker check, frontend build, runtime readiness, and live local mock handoff; latest evidence is spec `#13`, signal event `#11`, gateway response `mock_accepted`, and runtime `target_kind=local_mock`. Running the same runner without `--confirm-local-mock-handoff` refused to run and exited 2.
- Warning only: Vite reported stale browser baseline data and large bundle chunks.
- Warning only: Analytics smoke used a fake snapshot session because local `SNAPSHOT_DATABASE_URL` default Postgres was not reachable during test.
- Warning only: WebSocket smoke used a fake snapshot session because local `SNAPSHOT_DATABASE_URL` default Postgres was not reachable during test.
- Deferred: GitHub upload is intentionally skipped per user request; previous `git push -u origin codex/ai-agent-multitenant-foundation` attempts failed with `could not read Username for 'https://github.com': Device not configured`.

## Known Not-Accepted Items

- Real Casdoor JWKS/issuer/audience environment values still need to be configured and accepted with a live login token.
- Redis distributed admission leases, persisted high-risk confirmation responses, runner heartbeats, dispatch queue persistence, and Hyper AI/Prompt/Signal/Program/Attribution serialized worker handlers are implemented for cross-instance capacity/confirmation/routing coordination; live distributed worker acceptance with running Postgres/Redis and real model credentials is still pending.
- Dedicated full-page AI Trading rich backtest result route is implemented as a read-only evidence route; authenticated click-through acceptance with real saved Strategy Specs and Program Backtest evidence remains pending.
- AI Trading signal gateway live acceptance with the real HyperAlpha order backend URL/token is still pending; the endpoint is implemented, disabled by default, has local V1 contract regression/contract documentation, and now has a production handoff readiness checker, but no real live order-backend URL/token acceptance has been run.
- Live DeepSeek/Qwen API acceptance with a real user Hyper AI profile/API key remains pending; the model-adjust bridge is implemented and tested with a mocked Qwen response, then routed through the deterministic safety parser.
- End-to-end browser acceptance with real logged-in Hyper Insight sessions is still pending; local dev browser acceptance is complete for the V1 flow.
- Full local browser click-flow acceptance from draft/save/adjust/approve/backtest evidence/signal reject/mock handoff is complete; production-like logged-in user/profile acceptance remains separate.
- Local Postgres/backend readiness blocker has been cleared for this machine. LaunchAgent runtime-mirror startup is installed and has self-healed frontend/backend/mock gateway after local service termination; an actual macOS reboot has not been physically performed in this session, and future code changes require rerunning `scripts/local-dev/install_launch_agent.sh` to resync the runtime copy.
- Existing startup migrations/model validation are Postgres-oriented and not suitable for an ad hoc SQLite browser acceptance environment without a dedicated dev fallback path.
- Real exchange execution acceptance is still pending; this slice adds automated hard-risk preflight but does not execute a live order for validation.
- Live Discord Gateway acceptance with real Discord bot credentials is still pending; backend runtime is now per-user but only fake-client lifecycle was tested locally.
- Factor computation/value storage is still global by factor name; private custom factors are now excluded from shared precompute/effectiveness storage, but a dedicated per-user factor value schema is still needed if private custom factors should be precomputed instead of computed on demand.
