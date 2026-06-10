# HyperAlpha Implementation Handoff

This repository is the local HyperAlpha fork point for adapting the open-source AI trading framework to `hyperalpha.org`.

## Product Direction

Use this project as the user-facing AI trading framework:

- AI Trader and Program Trader remain the core product concepts.
- DeepSeek and Qwen are the initial model providers.
- Hyperliquid is the only V1 trading venue.
- The product uses Hyperliquid core perps plus HIP-3 builder markets such as `xyz:NVDA`, `xyz:TSLA`, `xyz:SP500`, and `xyz:XYZ100`.
- Users can adjust strategies through natural language.
- The AI produces strategy plans, constraints, and structured trade signals.
- HyperAlpha's existing backend is the only system that sends live orders.

## Required Boundary

The AI runtime must not submit orders directly.

Required flow:

```text
AI strategy/runtime
  -> structured signal
  -> hard risk validation
  -> HTTP JSON handoff
  -> HyperAlpha order backend
  -> order/fill/reject event ingestion
  -> UI state and audit log
```

Current V1 implementation supports HTTP JSON handoff only. The AI Trading
runtime and production readiness checker expose `AI_TRADING_SIGNAL_GATEWAY_MODE`
as a non-secret config field and fail closed unless it is `http`; RabbitMQ can
still be used behind the HyperAlpha order backend, but a direct Agent-to-RabbitMQ
adapter is not accepted in this V1 path.

## First Implementation Slice

Build the first vertical slice in this order:

1. Hyperliquid market registry.
   - Core perp markets.
   - HIP-3 `xyz` markets.
   - Top 20 / Top 50 by volume or open interest.
   - Exclude delisted markets.
   - Preserve DEX-prefixed symbols.

2. DeepSeek and Qwen model profile UX.
   - Provider, base URL, model, temperature.
   - Use OpenAI-compatible request format internally.

3. Strategy spec builder.
   - Natural-language prompt to structured strategy JSON.
   - Natural-language edits to spec patch.
   - User approval before saving strategy changes.

4. Hyperliquid backtest loader.
   - Use Hyperliquid candles.
   - Include fees, funding, long/short, leverage, stop-loss, take-profit, and symbol attribution.

5. Signal runtime.
   - Build AI context packets.
   - Ask model for JSON signal.
   - Validate schema and hard constraints.
   - Emit signal to HyperAlpha order backend.

## Existing Backend Integration Notes

The Lark "Hyper下单API" document shows RabbitMQ-based messaging.

Observed queues:

- `QUEUE_STRATEGY_TREND`
- `QUEUE_STRATEGY_MATRIX`
- `QUEUE_STRATEGY_GRID`
- `QUEUE_STRATEGY_LS`

Observed constraints:

- Message TTL: 10 minutes.
- Subscribe directly to queues.
- Do not declare extra bindings.

Observed envelope:

```json
{
  "type": "ORDER_FULL_FILLED",
  "data": {}
}
```

If a future direct RabbitMQ handoff is required, confirm whether a new queue such
as `QUEUE_AI_TRADING_SIGNAL` is allowed or whether AI signals must be routed into
an existing queue, then add a separate adapter, readiness gate, and acceptance
evidence before enabling it.

## Source Documents

- Full PRD: `docs/hyperalpha/ai-trading-prd.md`
- Lark backend API document: user-provided Hyper下单API link
