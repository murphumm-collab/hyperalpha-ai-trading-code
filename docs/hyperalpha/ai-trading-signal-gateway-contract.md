# HyperAlpha AI Trading Signal Gateway Contract

Status: V1 local contract, HTTP JSON handoff, disabled by default.

## Purpose

AI Trading emits reviewed trade signals only. The AI agent and AI Trading API must not place exchange orders directly.

The downstream HyperAlpha order backend is the only component allowed to translate an eligible signal into real order intent, apply final account/risk checks, and submit to Hyperliquid.

## Enablement

The gateway is off unless all required runtime config is present:

- `AI_TRADING_SIGNAL_GATEWAY_ENABLED=true`
- `AI_TRADING_SIGNAL_GATEWAY_URL=https://...`
- `AI_TRADING_SIGNAL_GATEWAY_TOKEN=...` optional bearer token
- `AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS=900` by default

When the gateway is disabled or missing a URL, `/api/ai-trading/signal-events/{id}/handoff` returns `409` and writes a blocked audit attempt. It does not submit to the order backend.

## HTTP Request

Method: `POST`

Headers:

```http
Content-Type: application/json
Authorization: Bearer <AI_TRADING_SIGNAL_GATEWAY_TOKEN>
```

The authorization header is sent only to the order backend. It is never included in AI model context, public API responses, or handoff attempt responses.

## Required Payload

```json
{
  "type": "AI_TRADING_SIGNAL_CANDIDATE",
  "version": "hyperalpha.ai_trading.gateway_message.v1",
  "contract": {
    "name": "AI_TRADING_SIGNAL_CANDIDATE",
    "version": "hyperalpha.ai_trading.gateway_message.v1",
    "signal_version": "hyperalpha.ai_trading.signal_candidate.v1",
    "delivery": "http_json_post",
    "order_authority": "order_backend_only"
  },
  "signal_event_id": 123,
  "strategy_spec_id": 456,
  "user_id": 789,
  "venue": "hyperliquid",
  "symbol": "BTC",
  "exchange_symbol": "BTC",
  "action": "buy",
  "idempotency_key": "signal_event:123",
  "signal_created_at": "2026-06-09T00:00:00+00:00",
  "signal_age_seconds": 12,
  "max_handoff_age_seconds": 900,
  "user_confirmation": {
    "confirmed": true,
    "source": "hyper_ai_recent_signal_panel"
  },
  "market": {},
  "market_context": {},
  "risk": {},
  "backtest": {},
  "execution_boundary": {},
  "validation": {},
  "signal": {}
}
```

Top-level fields are the stable order-backend contract. The nested `signal` object is a redacted copy of the full reviewed signal candidate for audit and debugging.

## Handoff Gates

A signal is eligible only when all of these are true:

- Current authenticated user owns the signal event.
- Event status is `review_candidate` and handoff status is not `submitted`.
- Gateway is enabled and URL is configured.
- Signal event is younger than `AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS`, unless the age gate is explicitly set to `0`.
- Request body includes `confirmed_by_user=true`.
- Persisted signal version is `hyperalpha.ai_trading.signal_candidate.v1`.
- Persisted signal candidate type is `review_signal_candidate`.
- Venue is `hyperliquid`.
- Signal action is tradeable: `buy` or `sell`.
- Signal action and symbol match the immutable audit event action and symbol.
- Backtest evidence is accepted and has parseable positive trade count, max drawdown, and at least one performance metric.
- Validation keeps `eligible_for_backend_handoff=true`.
- Execution boundary keeps `signal_only=true`, `not_an_order=true`, `requires_user_confirmation=true`, `ai_may_place_orders=false`, and `order_backend_only=true`.

## Order Backend Responsibilities

The order backend must treat this payload as signal input, not as an order:

- Resolve the target user account and API credentials outside the AI payload.
- Re-run account-level and exchange-level risk checks.
- Reject stale, duplicated, or already-consumed `idempotency_key` values.
- Convert `action`, `symbol`, `risk`, and strategy constraints into the backend's own order model.
- Emit order/fill/reject events back into platform audit state.

The AI Trading gateway does not include exchange API keys, private keys, raw order size, or direct exchange order IDs.

## Response Audit

Handoff attempts store only a non-secret response summary for downstream audit:

- Always record HTTP status code when available.
- Optionally record whitelisted JSON fields only: `accepted`, `status`, `idempotency_key`, `signal_event_id`, `order_backend_signal_id`, `request_id`, and `code`.
- Never store gateway URL, bearer token, authorization headers, response body, raw error message, or arbitrary downstream response fields in public attempt responses.
- Failed handoffs store sanitized error type/status summaries instead of raw exception strings.

## Verification

Contract regression is covered by `backend/tests/test_ai_trading_routes.py`:

- `test_ai_trading_signal_gateway_payload_contract_is_stable_signal_only`
- `test_ai_trading_strategy_signal_and_handoff_flow`
- Redaction, response-summary, and blocker-specific handoff tests

## Local Mock Gateway

For local/browser acceptance without touching the real order backend:

```bash
cd backend
uv run uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1
```

Point the main backend at the mock gateway:

```bash
AI_TRADING_SIGNAL_GATEWAY_ENABLED=true
AI_TRADING_SIGNAL_GATEWAY_URL=http://127.0.0.1:5621/api/ai-trading/signals
AI_TRADING_SIGNAL_GATEWAY_TOKEN=local-mock-token
```

Accepted mock payloads are appended to `backend/logs/ai_trading_mock_gateway.jsonl` unless `AI_TRADING_MOCK_GATEWAY_LOG` is set.
