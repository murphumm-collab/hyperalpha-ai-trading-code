"""
AI Shared Tools - Common tools for AI Program and AI Prompt Generation services

Provides tools for:
- Signal pool configuration access
- Signal backtest execution
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Signal metric explanations for AI context
SIGNAL_METRIC_EXPLANATIONS = {
    "cvd": {
        "name": "Cumulative Volume Delta",
        "description": "Taker Buy Volume - Taker Sell Volume in USD. Positive = buying pressure, Negative = selling pressure.",
        "typical_range": "±5M to ±50M for BTC",
        "interpretation": "CVD > 15M suggests strong buying; CVD < -15M suggests strong selling"
    },
    "oi_delta": {
        "name": "Open Interest Change %",
        "description": "Percentage change in open interest. Shows new positions entering or exiting.",
        "typical_range": "±0.5% to ±3%",
        "interpretation": "> 1% with price up = new longs; > 1% with price down = new shorts"
    },
    "oi": {
        "name": "Open Interest Change (USD)",
        "description": "Absolute change in open interest in USD.",
        "typical_range": "±10M to ±100M for BTC",
        "interpretation": "Rising OI = new positions; Falling OI = positions closing"
    },
    "taker_ratio": {
        "name": "Taker Buy/Sell Ratio",
        "description": "Ratio of taker buy volume to taker sell volume.",
        "typical_range": "0.3 to 3.0",
        "interpretation": "> 2.0 = aggressive buying; < 0.5 = aggressive selling"
    },
    "volume": {
        "name": "Trading Volume",
        "description": "Total trading volume in USD for the period.",
        "typical_range": "> 10M to > 50M for significance",
        "interpretation": "High volume confirms price moves; low volume suggests weak moves"
    },
    "funding_rate": {
        "name": "Funding Rate",
        "description": "Perpetual funding rate percentage.",
        "typical_range": "-0.05% to +0.05%",
        "interpretation": "> 0.01% = longs pay shorts (bullish sentiment); < -0.01% = shorts pay longs"
    }
}


def _missing_user_context_result() -> str:
    return json.dumps({
        "error": "Authenticated user context is required.",
        "reason": "missing_user_context",
    })


# Tool definitions in OpenAI format (shared between services)
SHARED_SIGNAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_signal_pools",
            "description": "Get configured signal pools and their signal conditions. Returns pool names, logic (AND/OR), monitored symbols, exchange, and detailed signal definitions with metric explanations. Use this to understand what triggers the AI Trader.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "enum": ["hyperliquid", "binance", "all"],
                        "description": "Filter signal pools by exchange. Use 'all' to get pools from all exchanges (default: all)",
                        "default": "all"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_signal_backtest",
            "description": "Run a backtest on a signal pool to check trigger frequency and see sample triggers. Returns trigger count, average frequency, and recent trigger examples. The backtest uses the exchange configured in the signal pool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pool_id": {
                        "type": "integer",
                        "description": "Signal pool ID to backtest"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol to backtest (e.g., 'BTC')",
                        "default": "BTC"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Lookback hours for backtest (default: 24, max: 168)",
                        "default": 24
                    }
                },
                "required": ["pool_id"]
            }
        }
    }
]


def execute_get_signal_pools(db, exchange: str = "all", user_id: Optional[int] = None) -> str:
    """
    Execute get_signal_pools tool - returns signal pools with explanations.

    Args:
        db: SQLAlchemy database session
        exchange: Filter by exchange ('hyperliquid', 'binance', or 'all')

    Returns:
        JSON string with signal pools and metric explanations
    """
    from database.models import SignalDefinition, SignalPool

    if user_id is None:
        return _missing_user_context_result()

    try:
        # Get signal definitions (with exchange filter if needed)
        signals_query = db.query(SignalDefinition).filter(
            SignalDefinition.user_id == user_id,
            SignalDefinition.is_deleted != True,
        )
        if exchange and exchange != "all":
            signals_query = signals_query.filter(SignalDefinition.exchange == exchange)
        signals_result = signals_query.order_by(SignalDefinition.id).all()

        signals_map = {}
        for signal in signals_result:
            trigger_condition = signal.trigger_condition
            if isinstance(trigger_condition, str):
                trigger_condition = json.loads(trigger_condition)
            signals_map[signal.id] = {
                "id": signal.id,
                "name": signal.signal_name,
                "description": signal.description,
                "condition": trigger_condition,
                "enabled": signal.enabled,
                "exchange": signal.exchange or "hyperliquid",
            }

        # Get signal pools (with exchange filter if needed)
        pools_query = db.query(SignalPool).filter(
            SignalPool.user_id == user_id,
            SignalPool.is_deleted != True,
        )
        if exchange and exchange != "all":
            pools_query = pools_query.filter(SignalPool.exchange == exchange)
        pools_result = pools_query.order_by(SignalPool.id).all()

        pools = []
        for pool in pools_result:
            signal_ids = pool.signal_ids
            if isinstance(signal_ids, str):
                signal_ids = json.loads(signal_ids)
            symbols = pool.symbols
            if isinstance(symbols, str):
                symbols = json.loads(symbols)

            pool_exchange = pool.exchange or "hyperliquid"
            source_type = pool.source_type or "market_signals"
            source_config = pool.source_config or {}
            if isinstance(source_config, str):
                try:
                    source_config = json.loads(source_config)
                except json.JSONDecodeError:
                    source_config = {}

            # Get signal details for this pool
            pool_signals = []
            if source_type == "market_signals":
                for sig_id in (signal_ids or []):
                    if sig_id in signals_map:
                        sig = signals_map[sig_id]
                        cond = sig["condition"]
                        metric = cond.get("metric", "unknown")
                        pool_signals.append({
                            "id": sig_id,
                            "name": sig["name"],
                            "description": sig["description"],
                            "metric": metric,
                            "operator": cond.get("operator", ""),
                            "threshold": cond.get("threshold", ""),
                            "time_window": cond.get("time_window", "5m"),
                            "metric_explanation": SIGNAL_METRIC_EXPLANATIONS.get(metric, {})
                        })

            pools.append({
                "id": pool.id,
                "name": pool.pool_name,
                "exchange": pool_exchange,
                "source_type": source_type,
                "logic": pool.logic or "OR",
                "symbols": symbols or [],
                "enabled": pool.enabled,
                "signals": pool_signals,
                "source_config": source_config if source_type == "wallet_tracking" else {}
            })

        result = {
            "exchange_filter": exchange,
            "total_pools": len(pools),
            "pools": pools,
            "note": "Use run_signal_backtest tool to check trigger frequency for a specific pool."
        }

        if not pools:
            if exchange and exchange != "all":
                result["suggestion"] = f"No signal pools configured for {exchange}. Consider creating a signal pool for this exchange."
            else:
                result["suggestion"] = "No signal pools configured. Consider creating a signal pool to trigger AI decisions based on market conditions."

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"[get_signal_pools] Error: {e}")
        return json.dumps({"error": str(e)})


def execute_run_signal_backtest(
    db,
    pool_id: int,
    symbol: str = "BTC",
    hours: int = 24,
    user_id: Optional[int] = None,
) -> str:
    """
    Execute run_signal_backtest tool - runs backtest and returns trigger statistics.

    Args:
        db: SQLAlchemy database session
        pool_id: Signal pool ID to backtest
        symbol: Trading symbol (default: BTC)
        hours: Lookback hours (default: 24, max: 168)

    Returns:
        JSON string with backtest results
    """
    from services.signal_backtest_service import signal_backtest_service
    from database.models import SignalPool

    if user_id is None:
        return _missing_user_context_result()

    try:
        pool_exists = db.query(SignalPool.id).filter(
            SignalPool.id == pool_id,
            SignalPool.user_id == user_id,
            SignalPool.is_deleted != True,
        ).first()
        if not pool_exists:
            return json.dumps({"error": f"Signal pool {pool_id} not found"})

        # Limit hours to reasonable range
        hours = min(max(hours, 1), 168)  # 1 hour to 7 days

        # Calculate timestamp range
        now = datetime.now(timezone.utc)
        end_ts = int(now.timestamp() * 1000)
        start_ts = int((now - timedelta(hours=hours)).timestamp() * 1000)

        logger.info(f"[run_signal_backtest] pool_id={pool_id}, symbol={symbol}, hours={hours}")

        # Run backtest
        backtest_result = signal_backtest_service.backtest_pool(
            db, pool_id, symbol, start_ts, end_ts
        )

        if "error" in backtest_result:
            return json.dumps({"error": backtest_result["error"]})

        # Extract key statistics
        triggers = backtest_result.get("triggers", [])
        trigger_count = len(triggers)

        # Calculate frequency
        if trigger_count > 0:
            avg_per_hour = trigger_count / hours
            if avg_per_hour >= 1:
                frequency_desc = f"{avg_per_hour:.1f} triggers per hour"
            else:
                hours_per_trigger = hours / trigger_count
                frequency_desc = f"1 trigger every {hours_per_trigger:.1f} hours"
        else:
            frequency_desc = "No triggers in this period"

        # Get recent trigger samples (last 5)
        recent_triggers = []
        for t in triggers[-5:]:
            trigger_time = datetime.fromtimestamp(t["timestamp"] / 1000, tz=timezone.utc)
            recent_triggers.append({
                "time": trigger_time.strftime("%Y-%m-%d %H:%M UTC"),
                "signals": [s.get("signal_name", "Unknown") for s in t.get("triggered_signals", [])]
            })

        result = {
            "pool_id": pool_id,
            "pool_name": backtest_result.get("pool_name", "Unknown"),
            "symbol": symbol,
            "backtest_period": f"{hours} hours",
            "trigger_count": trigger_count,
            "frequency": frequency_desc,
            "recent_triggers": recent_triggers,
        }

        # Add recommendations based on frequency
        if trigger_count == 0:
            result["recommendation"] = "No triggers found. Consider lowering thresholds or extending the backtest period."
        elif avg_per_hour > 10:
            result["recommendation"] = "Very high trigger frequency. Consider raising thresholds to reduce noise."
        elif avg_per_hour > 2:
            result["recommendation"] = "High trigger frequency. May lead to overtrading."
        elif avg_per_hour < 0.1:
            result["recommendation"] = "Low trigger frequency. Thresholds may be too strict."
        else:
            result["recommendation"] = "Trigger frequency looks reasonable."

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"[run_signal_backtest] Error: {e}")
        return json.dumps({"error": str(e)})
