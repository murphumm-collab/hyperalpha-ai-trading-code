# HyperAlpha AI Trading PRD and Technical Plan

Status: Draft v0.1  
Date: 2026-06-06  
Owner: HyperAlpha product / trading platform team

## 1. Goal

Build an AI trading product on `hyperalpha.org` using an open-source AI trading framework as the base, modified for Hyperliquid and HIP-3 markets.

The product should let users:

- Select high-liquidity Hyperliquid crypto and HIP-3 equity/index markets.
- Choose an AI model provider, initially DeepSeek or Qwen.
- Create or adjust strategies in natural language.
- Run backtests on Hyperliquid market data.
- Convert approved strategies into executable signal policies.
- Receive AI-generated trade plans and constrained trade signals.
- Send those signals to the existing HyperAlpha trading backend, which owns real order submission.

The AI layer does not directly place orders. It produces structured strategy plans, constraints, and trade signals. HyperAlpha's backend remains the only order-sending authority.

## 2. Current Vibe-Trading Capability Assessment

Vibe-Trading is useful as a research, strategy generation, and backtest layer.

Existing strengths:

- Natural-language strategy generation through an AI agent.
- ReAct-style research loop with tool calls and streaming progress.
- Backtest execution and artifact generation.
- Run detail pages with equity curves, metrics, trades, code, and validation.
- Strategy comparison and correlation analysis.
- Alpha Zoo / factor research concepts.
- Multi-provider LLM settings, including OpenAI-compatible providers.
- Early live-trading concepts such as mandate, runner status, kill switch, and order guard.

Important gaps for HyperAlpha:

- No production Hyperliquid connector.
- No HIP-3 market discovery across builder DEXes such as `xyz`.
- No Hyperliquid-specific K-line loader, WebSocket market feed, order book, funding, OI, or account state adapter.
- No To C multi-user product layer.
- No native DeepSeek/Qwen productized model-selector flow for users.
- No signal handoff contract to HyperAlpha's existing order backend.
- No production execution layer, fill reconciliation, or order-state sync.

Recommended use:

- Keep Vibe-Trading ideas for strategy generation, backtest reports, and research UX.
- Do not use Vibe-Trading as the main To C trading platform.
- Use the open-source AI trading framework as the main app, and add selected Vibe-Trading-inspired modules.

## 3. Product Scope

### In Scope for V1

- HyperAlpha-hosted web product on the team's own domain.
- AI Trader creation and editing.
- DeepSeek and Qwen model support.
- Hyperliquid mainnet live trading workflow.
- Hyperliquid market data only.
- Crypto top 20 or top 50 by liquidity/volume.
- HIP-3 equity/index markets top 20 or top 50 by liquidity/volume.
- Natural-language strategy adjustment.
- Backtest before strategy enablement.
- AI-generated strategy plan and hard constraints.
- AI-generated trade signals.
- Signal delivery to HyperAlpha order backend.
- Execution/fill status ingestion from existing backend channels.

### Out of Scope for V1

- User auth and account system.
- User API key custody and management.
- Actual order submission implementation.
- Wallet/agent-wallet management.
- Billing.
- Copy trading.
- Social/trader leaderboard.
- Multi-exchange support beyond Hyperliquid.
- User-created arbitrary Python code execution in production.

## 4. User Workflow

1. User opens HyperAlpha AI Trading.
2. User selects market universe:
   - Crypto Top 20 / Top 50.
   - US Stocks / Indices Top 20 / Top 50 via HIP-3.
3. User chooses AI model:
   - DeepSeek.
   - Qwen.
4. User describes strategy in natural language.
5. AI converts prompt into:
   - Strategy thesis.
   - Market universe.
   - Entry conditions.
   - Exit conditions.
   - Position sizing constraints.
   - Stop-loss / take-profit rules.
   - Risk constraints.
6. User can modify the strategy using natural language.
7. System runs backtest on Hyperliquid historical data.
8. User reviews:
   - PnL.
   - Max drawdown.
   - Sharpe / Sortino.
   - Win rate.
   - Trade count.
   - Worst trade.
   - Symbol-level attribution.
   - AI explanation.
9. User enables strategy.
10. Runtime engine evaluates markets.
11. AI produces structured signals only.
12. Risk layer validates signals.
13. HyperAlpha backend receives accepted signals and sends orders.
14. UI displays order, fill, position, and PnL status.

## 5. Market Universe

### Crypto Markets

Source:

- Hyperliquid core perpetual metadata and asset contexts.

Selection:

- Sort active markets by 24h notional volume and/or open interest.
- Offer Top 20 and Top 50 presets.
- Exclude delisted markets.
- Optionally exclude markets below minimum depth or volume.

Initial likely core set:

- BTC
- ETH
- SOL
- XRP
- DOGE
- BNB
- SUI
- HYPE
- LINK
- AVAX

Final list must be dynamic.

### HIP-3 Equity / Index Markets

Source:

- Hyperliquid HIP-3 builder DEX metadata, especially `xyz` initially.
- Market names must retain the DEX prefix, for example `xyz:NVDA`, `xyz:SP500`.

Selection:

- Sort by 24h notional volume, open interest, and active status.
- Offer Top 20 and Top 50 presets.
- Exclude delisted markets.
- Flag `onlyIsolated` markets.

Initial likely watchlist:

- `xyz:SP500`
- `xyz:XYZ100`
- `xyz:NVDA`
- `xyz:TSLA`
- `xyz:AAPL`
- `xyz:MSFT`
- `xyz:META`
- `xyz:GOOGL`
- `xyz:AMZN`
- `xyz:AMD`
- `xyz:COIN`
- `xyz:MSTR`

### Market Registry Schema

```json
{
  "venue": "hyperliquid",
  "dex": "core",
  "coin": "BTC",
  "display_symbol": "BTC",
  "category": "crypto",
  "asset_id": 0,
  "max_leverage": 40,
  "size_decimals": 5,
  "mark_price": 0,
  "open_interest": 0,
  "volume_24h": 0,
  "funding": 0,
  "only_isolated": false,
  "is_delisted": false,
  "tradable": true,
  "risk_tier": "core"
}
```

For HIP-3:

```json
{
  "venue": "hyperliquid",
  "dex": "xyz",
  "coin": "xyz:NVDA",
  "display_symbol": "NVDA",
  "category": "us_stock",
  "asset_id": 110002,
  "tradable": true
}
```

Asset ID calculation must follow Hyperliquid's official HIP-3 asset ID rules. Do not infer from display symbol.

## 6. AI Model Layer

### Providers

V1 providers:

- DeepSeek.
- Qwen.

Use an OpenAI-compatible internal interface:

```json
{
  "provider": "deepseek",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat",
  "temperature": 0.2,
  "max_tokens": 4000
}
```

```json
{
  "provider": "qwen",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "model": "qwen-plus",
  "temperature": 0.2,
  "max_tokens": 4000
}
```

### AI Responsibilities

AI may:

- Explain market conditions.
- Generate strategy drafts.
- Translate user natural language into strategy specs.
- Suggest risk constraints.
- Evaluate signal context.
- Produce structured trade signal candidates.
- Explain why a signal was or was not produced.

AI must not:

- Directly send orders.
- Override platform risk limits.
- Increase leverage beyond configured limits.
- Trade delisted markets.
- Trade outside the approved market universe.
- Change user API keys or account settings.
- Execute arbitrary code in production.

## 7. Strategy Specification

All strategies should compile into a structured strategy spec.

```json
{
  "strategy_id": "strat_123",
  "name": "AI Trend Pullback",
  "model_provider": "deepseek",
  "model_name": "deepseek-chat",
  "universe": ["BTC", "ETH", "SOL", "xyz:NVDA"],
  "timeframes": ["5m", "15m", "1h"],
  "entry_rules": [
    "trend aligned on 1h",
    "5m pullback resolves upward",
    "volume expansion confirms move"
  ],
  "exit_rules": [
    "stop_loss",
    "take_profit",
    "trend_invalidated"
  ],
  "risk": {
    "max_position_notional_usd": 1000,
    "max_leverage": 2,
    "max_daily_loss_usd": 100,
    "max_trades_per_day": 10,
    "max_open_positions": 3,
    "require_stop_loss": true
  },
  "status": "draft"
}
```

Natural-language edits update this spec through an AI parser, then the system shows the diff to the user.

Example user edit:

> 只交易 BTC 和 NVDA，最大杠杆 2 倍，连续亏 3 次暂停，财报日前一天不要交易美股。

Expected spec patch:

```json
{
  "universe": ["BTC", "xyz:NVDA"],
  "risk": {
    "max_leverage": 2,
    "max_consecutive_losses": 3
  },
  "market_filters": {
    "avoid_equity_earnings_window": true,
    "earnings_blackout_days_before": 1
  }
}
```

## 8. Backtesting

### Data Source

Use Hyperliquid data only for V1.

Required data:

- Candles from Hyperliquid `candleSnapshot`.
- Mark price / mid price.
- Funding rate history where available.
- Open interest / volume snapshots where available.
- HIP-3 market metadata.

### Backtest Requirements

Backtest engine must support:

- Perpetual long/short.
- Fees.
- Funding.
- Leverage.
- Position sizing.
- Stop-loss.
- Take-profit.
- Trailing stop.
- Reduce-only exits.
- Multi-symbol portfolio.
- Delisted-market exclusion.
- Per-symbol attribution.

### Backtest Outputs

```json
{
  "backtest_id": "bt_123",
  "strategy_id": "strat_123",
  "period": {
    "start": "2026-01-01",
    "end": "2026-06-06"
  },
  "metrics": {
    "total_return": 0.18,
    "max_drawdown": -0.07,
    "sharpe": 1.4,
    "win_rate": 0.54,
    "trade_count": 86
  },
  "symbol_attribution": [
    {
      "coin": "BTC",
      "pnl": 1234,
      "trade_count": 20
    }
  ],
  "trades": [],
  "equity_curve": []
}
```

## 9. Runtime Signal Generation

Runtime loop:

1. Load enabled strategy.
2. Load approved market universe.
3. Pull realtime market snapshot.
4. Calculate deterministic indicators and factors.
5. Build AI context packet.
6. Ask AI for trade signal candidate.
7. Validate output schema.
8. Apply hard risk constraints.
9. Publish accepted signal to HyperAlpha trading backend.
10. Store signal, AI reasoning, validation result, and execution result.

### AI Context Packet

```json
{
  "strategy": {},
  "market_snapshot": {
    "coin": "BTC",
    "timeframe": "5m",
    "mark_price": 100000,
    "funding": 0.0001,
    "open_interest": 1000000000,
    "volume_24h": 500000000
  },
  "positions": [],
  "risk_state": {
    "daily_loss": 0,
    "trades_today": 2,
    "halted": false
  }
}
```

### Signal Output Schema

```json
{
  "type": "TRADE_SIGNAL",
  "strategy_id": "strat_123",
  "coin": "BTC",
  "action": "OPEN_LONG",
  "confidence": 0.72,
  "order_preference": {
    "order_type": "market",
    "reduce_only": false
  },
  "risk": {
    "max_notional_usd": 500,
    "stop_loss_px": 98000,
    "take_profit_px": 104000,
    "max_slippage_bps": 20
  },
  "reason": "Trend aligned on 1h and 5m pullback recovered with rising volume.",
  "expires_at": "2026-06-06T12:10:00Z"
}
```

### Hard Validation

Reject signal if:

- Symbol is not tradable.
- Symbol is outside strategy universe.
- Market is delisted.
- Signal is expired.
- Confidence below threshold.
- Stop-loss missing when required.
- Max notional exceeds user/platform limit.
- Leverage exceeds limit.
- Daily loss limit reached.
- Max trades per day reached.
- Existing position conflict.
- Duplicate signal within cooldown window.
- Market data is stale.

## 10. Integration With HyperAlpha Trading Backend

The Lark document shows two relevant integration paths:

### RabbitMQ Pub/Sub

Observed from Lark:

- Messaging uses RabbitMQ publish/subscribe.
- Queue names:
  - `QUEUE_STRATEGY_TREND` for trend strategy.
  - `QUEUE_STRATEGY_MATRIX` for intelligent copy-trading strategy.
  - `QUEUE_STRATEGY_GRID` for grid strategy.
  - `QUEUE_STRATEGY_LS` for long/short copy-trading strategy.
- Message TTL is 10 minutes.
- Subscribe directly to queues. Do not declare extra bindings.
- Message envelope:

```json
{
  "type": "ORDER_FULL_FILLED",
  "data": {}
}
```

Observed fill example fields:

```json
{
  "type": "ORDER_FULL_FILLED",
  "data": {
    "user": "0x6a572bb9d31ff710f882f33c21d8ba11a169a887",
    "dir": "Open Short",
    "coin": "BTC",
    "sz": 1.44906
  }
}
```

### HTTP Internal Call

The Lark page contains sections for:

- HTTP internal calls.
- Business status codes.
- API list.

The current draft needs the exact endpoint fields from the Lark API table before implementation.

### Proposed Signal Handoff

For AI-generated signals, introduce a dedicated message type:

```json
{
  "type": "AI_TRADE_SIGNAL",
  "data": {
    "signal_id": "sig_123",
    "strategy_id": "strat_123",
    "user_id": "user_123",
    "coin": "BTC",
    "dex": "core",
    "action": "OPEN_LONG",
    "max_notional_usd": 500,
    "reduce_only": false,
    "stop_loss_px": 98000,
    "take_profit_px": 104000,
    "confidence": 0.72,
    "reason": "Trend aligned on 1h and 5m pullback recovered.",
    "expires_at": "2026-06-06T12:10:00Z"
  }
}
```

Recommended queue:

- If the existing backend requires strategy queues, route trend-style AI signals to `QUEUE_STRATEGY_TREND`.
- If backend can accept a new queue, create `QUEUE_AI_TRADING_SIGNAL`.

The trading backend should respond through existing order lifecycle messages such as filled, rejected, canceled, or partial-filled events.

## 11. Realtime Data Plan

### Market Data

Use Hyperliquid WebSocket for realtime data:

- `allMids`
- `trades`
- `l2Book`
- `candle`
- `userEvents`
- `orderUpdates`
- `userFills`

Use REST as fallback:

- `metaAndAssetCtxs`
- `candleSnapshot`
- `clearinghouseState`
- `frontendOpenOrders`
- `userFills`
- `orderStatus`

### Architecture

```text
Hyperliquid WebSocket
  -> market-data-service
  -> Redis latest snapshot
  -> strategy-runtime worker
  -> AI model
  -> signal validator
  -> RabbitMQ / HTTP signal handoff
  -> HyperAlpha order backend
  -> order/fill event consumer
  -> PostgreSQL + frontend
```

### Staleness Rules

- Reject signals if candle data is stale.
- Reject signals if mark price is stale.
- Pause strategy if WebSocket reconnect loop fails repeatedly.
- Fall back to REST snapshot before hard halt.
- Emit UI warning when market data confidence is degraded.

## 12. Frontend Pages

### Market Universe

- Crypto Top 20 / Top 50.
- US Stocks / Indices Top 20 / Top 50.
- Search by symbol.
- Category filters:
  - Crypto.
  - US Stocks.
  - Indices.
  - Commodities.
  - FX.
- Columns:
  - Symbol.
  - DEX.
  - Category.
  - Mark price.
  - 24h volume.
  - OI.
  - Funding.
  - Max leverage.
  - Tradable status.

### AI Trader Builder

- Select model: DeepSeek / Qwen.
- Select universe preset.
- Natural-language strategy box.
- Strategy constraints editor.
- AI-generated strategy preview.
- User diff approval for natural-language edits.

### Backtest

- Select strategy.
- Select period.
- Run backtest.
- Display metrics, equity curve, trades, attribution, and AI diagnosis.

### Live Signals

- Current strategy status.
- Latest AI reasoning.
- Latest accepted/rejected signals.
- Risk validation result.
- Pending/filled/rejected order state from backend.

### Control Panel

- Enable strategy.
- Pause strategy.
- Emergency stop.
- Max daily loss.
- Max position notional.
- Max leverage.
- Max trades per day.

## 13. Backend Modules

Recommended service boundaries:

```text
apps/web
  Frontend pages and user workflows

apps/api
  User-facing API, strategy specs, backtests, model settings

services/market-data
  Hyperliquid REST/WebSocket ingestion

services/strategy-runtime
  Strategy scheduler and AI signal generation

services/backtest
  Historical data loading and backtest execution

services/signal-gateway
  RabbitMQ/HTTP handoff to trading backend

packages/ai
  DeepSeek/Qwen OpenAI-compatible adapters

packages/hyperliquid
  Market registry, candles, asset IDs, data normalization

packages/risk
  Hard risk validation
```

## 14. Data Model

Minimum tables:

- `ai_model_profiles`
- `market_registry`
- `strategy_specs`
- `strategy_versions`
- `backtest_runs`
- `backtest_trades`
- `runtime_signals`
- `risk_decisions`
- `execution_events`
- `strategy_runtime_state`

### Runtime Signal Table

```sql
CREATE TABLE runtime_signals (
  id TEXT PRIMARY KEY,
  strategy_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  coin TEXT NOT NULL,
  dex TEXT NOT NULL,
  action TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  payload JSONB NOT NULL,
  ai_reason TEXT,
  risk_status TEXT NOT NULL,
  risk_reasons JSONB NOT NULL DEFAULT '[]',
  execution_status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ
);
```

## 15. Implementation Phases

### Phase 0: Repo Setup

- Create local working repo from the open-source AI trading framework.
- Configure GitHub remote under HyperAlpha organization/account.
- Keep Vibe-Trading repo as reference, not the main product.

### Phase 1: Market Data and Universe

- Implement Hyperliquid core market registry.
- Implement HIP-3 `xyz` market registry.
- Add Top 20 / Top 50 dynamic filters.
- Add market data REST cache.
- Add WebSocket market-data service.

### Phase 2: AI Strategy Builder

- Add DeepSeek provider.
- Add Qwen provider.
- Add strategy spec schema.
- Add natural-language strategy creation.
- Add natural-language strategy edit with diff approval.

### Phase 3: Backtest

- Implement Hyperliquid candle loader.
- Implement perp backtest runner with fees/funding.
- Implement multi-symbol attribution.
- Build backtest UI.

### Phase 4: Signal Runtime

- Implement strategy scheduler.
- Implement AI context builder.
- Implement signal schema validator.
- Implement hard risk validator.
- Store signals and reasoning.

### Phase 5: Trading Backend Integration

- Map accepted AI signals to RabbitMQ or HTTP API.
- Consume order/fill/reject events.
- Display live signal and execution state.
- Add observability and retries.

### Phase 6: Production Controls

- Emergency stop.
- Per-user strategy pause.
- Global market-data degradation halt.
- Model failure fallback.
- Signal deduplication.
- Audit export.

## 16. Risks

### AI Risk

- Model may hallucinate invalid actions.
- Model may overtrade in noisy markets.
- Model latency may make signals stale.

Mitigation:

- Strict JSON schema.
- Hard risk validation.
- Signal expiry.
- Deterministic precomputed indicators.
- No direct order access for AI.

### Market Risk

- HIP-3 markets may have lower liquidity than core crypto markets.
- Equity perps trade 24/7 while underlying equities do not.
- Oracle/funding behavior can diverge from traditional market intuition.

Mitigation:

- Liquidity filters.
- Max slippage.
- Max notional.
- Earnings/event blackout.
- Market-specific risk tiers.

### Execution Risk

- Partial fills.
- Slippage.
- Delayed fill events.
- Duplicate signals.
- WebSocket disconnects.

Mitigation:

- Idempotency keys.
- Signal cooldown.
- Order status reconciliation.
- Dead-letter queue.
- Retry policy with max attempts.

## 17. Open Questions

Need exact answers before implementation:

1. Which GitHub organization/repository should receive the new local project?
2. Should the product fork `HammerGPT/Hyper-Alpha-Arena`, or should a new repo be created with selected concepts ported in?
3. What is the exact HTTP API contract from the Lark "API列表" section?
4. Can a new RabbitMQ queue `QUEUE_AI_TRADING_SIGNAL` be added, or must we reuse existing strategy queues?
5. Which order lifecycle message types are emitted besides `ORDER_FULL_FILLED`?
6. What user/account identifier should AI signals carry: wallet address, internal user id, or both?
7. What exact max loss / max leverage limits should be exposed in UI versus enforced only in backend?
8. Should V1 include only `xyz` HIP-3 markets, or discover every active HIP-3 DEX?

## 18. Recommended Immediate Next Step

Create the implementation repo locally, then push it to GitHub.

Recommended decision:

- Main repo: modified Hyper-Alpha-Arena.
- Add a `docs/` folder with this PRD.
- Add an `architecture/` folder for API contracts and diagrams.
- Implement the first slice as market discovery + DeepSeek/Qwen model config + strategy spec builder.

First coding slice:

```text
Market Universe + AI Strategy Builder

Inputs:
- Hyperliquid core markets
- HIP-3 xyz markets
- DeepSeek/Qwen model profile
- Natural-language strategy prompt

Outputs:
- Structured strategy spec
- Backtest-ready config
```

