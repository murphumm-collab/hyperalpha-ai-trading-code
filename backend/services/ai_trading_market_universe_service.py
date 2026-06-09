"""AI Trading market-universe helpers for Hyperliquid.

This module turns Hyperliquid core and HIP-3 metadata into a product-facing
market universe. It is read-only market discovery; it never touches account,
wallet, API-key, or order state.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from services.exchanges.symbol_mapper import SymbolMapper
from services.hyperliquid_symbol_service import META_ENDPOINTS, get_available_symbols


AI_TRADING_MARKET_UNIVERSE_CACHE_SECONDS = int(
    os.getenv("AI_TRADING_MARKET_UNIVERSE_CACHE_SECONDS", "300")
)

INDEX_MARKET_SYMBOLS = {
    "SP500",
    "SPX",
    "NASDAQ",
    "NDX",
    "DOW",
    "DJI",
    "XYZ100",
    "GOLD",
    "SILVER",
}

_market_universe_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}


def clear_ai_trading_market_universe_cache() -> None:
    """Clear cached market universe data. Intended for tests and admin reloads."""
    _market_universe_cache.clear()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_internal_symbol(raw_symbol: Any) -> str:
    return SymbolMapper.to_internal(str(raw_symbol or "").strip(), "hyperliquid").upper()


def _display_symbol(raw_symbol: Any, *, dex: Optional[str] = None) -> str:
    raw = str(raw_symbol or "").strip()
    if ":" in raw:
        return raw.split(":", 1)[1].upper()
    if dex:
        return _normalize_internal_symbol(raw)
    return raw.upper()


def _exchange_symbol(raw_symbol: Any, *, dex: Optional[str] = None) -> str:
    raw = str(raw_symbol or "").strip()
    if not dex:
        return raw.upper()
    if ":" in raw:
        return raw
    return f"{dex}:{raw.upper()}"


def _market_category(display_symbol: str, *, dex: Optional[str] = None) -> str:
    if not dex:
        return "crypto"
    if display_symbol.upper() in INDEX_MARKET_SYMBOLS:
        return "us_index"
    return "us_stock"


def _asset_id(entry: Dict[str, Any], index: int, *, dex: Optional[str] = None) -> Optional[int]:
    explicit = entry.get("assetId", entry.get("asset_id"))
    try:
        if explicit is not None and explicit != "":
            return int(explicit)
    except (TypeError, ValueError):
        return None
    if dex:
        return None
    return index


def _serialize_market(
    entry: Dict[str, Any],
    context: Dict[str, Any],
    *,
    index: int,
    dex: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if entry.get("isDelisted"):
        return None

    raw_symbol = entry.get("name") or entry.get("symbol") or entry.get("coin")
    internal_symbol = _normalize_internal_symbol(raw_symbol)
    if not internal_symbol:
        return None

    display = _display_symbol(raw_symbol, dex=dex)
    exchange_symbol = _exchange_symbol(raw_symbol, dex=dex)
    if dex:
        SymbolMapper.register_hip3_mapping(internal_symbol, exchange_symbol)

    category = _market_category(display, dex=dex)
    return {
        "venue": "hyperliquid",
        "dex": dex or "core",
        "symbol": internal_symbol,
        "coin": exchange_symbol if dex else internal_symbol,
        "exchange_symbol": exchange_symbol if dex else internal_symbol,
        "display_symbol": display,
        "name": entry.get("displayName") or entry.get("name") or display,
        "category": category,
        "asset_id": _asset_id(entry, index, dex=dex),
        "max_leverage": entry.get("maxLeverage"),
        "size_decimals": entry.get("szDecimals"),
        "mark_price": _safe_float(
            context.get("markPx") or context.get("midPx") or context.get("oraclePx")
        ),
        "open_interest": _safe_float(context.get("openInterest")),
        "volume_24h_usd": _safe_float(context.get("dayNtlVlm")),
        "volume_24h_base": _safe_float(context.get("dayBaseVlm")),
        "funding": _safe_float(context.get("funding")),
        "only_isolated": bool(entry.get("onlyIsolated")),
        "is_delisted": False,
        "tradable": True,
        "risk_tier": "core" if category == "crypto" else "hip3",
    }


def _fetch_meta_and_asset_contexts(
    *,
    environment: str,
    dex: Optional[str] = None,
) -> List[Dict[str, Any]]:
    endpoint = META_ENDPOINTS.get(environment, META_ENDPOINTS["mainnet"])
    payload: Dict[str, Any] = {"type": "metaAndAssetCtxs"}
    if dex:
        payload["dex"] = dex

    response = requests.post(endpoint, json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or len(data) < 2:
        raise ValueError("Unexpected Hyperliquid metaAndAssetCtxs response")

    meta = data[0] if isinstance(data[0], dict) else {}
    contexts = data[1] if isinstance(data[1], list) else []
    universe = meta.get("universe") if isinstance(meta, dict) else []
    if not isinstance(universe, list) or not isinstance(contexts, list):
        raise ValueError("Missing Hyperliquid universe or asset context list")

    markets: List[Dict[str, Any]] = []
    for index, entry in enumerate(universe):
        if not isinstance(entry, dict):
            continue
        context = contexts[index] if index < len(contexts) and isinstance(contexts[index], dict) else {}
        market = _serialize_market(entry, context, index=index, dex=dex)
        if market:
            markets.append(market)

    markets.sort(key=lambda item: item.get("volume_24h_usd") or 0, reverse=True)
    return markets


def _fallback_hip3_markets(hip3_dex: str) -> List[Dict[str, Any]]:
    markets: List[Dict[str, Any]] = []
    for index, entry in enumerate(get_available_symbols()):
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "hip3":
            continue
        market = _serialize_market(entry, {}, index=index, dex=hip3_dex)
        if market:
            markets.append(market)
    return markets


def _preset(markets: List[Dict[str, Any]], size: int, limit: int) -> List[Dict[str, Any]]:
    return markets[: min(size, limit)]


def get_ai_trading_market_universe(
    *,
    environment: str = "mainnet",
    limit: int = 50,
    hip3_dex: str = "xyz",
) -> Dict[str, Any]:
    """Return Crypto and HIP-3 Top 20/50 presets for the AI Trading product."""
    environment = environment if environment in {"mainnet", "testnet"} else "mainnet"
    hip3_dex = str(hip3_dex or "xyz").strip().lower()[:32] or "xyz"
    limit = max(1, min(int(limit or 50), 50))

    cache_key = (environment, hip3_dex)
    cached = _market_universe_cache.get(cache_key)
    now = time.time()
    if (
        cached
        and now - float(cached.get("cached_at") or 0) < AI_TRADING_MARKET_UNIVERSE_CACHE_SECONDS
    ):
        return cached["payload"]

    errors: Dict[str, str] = {}
    try:
        crypto_markets = _fetch_meta_and_asset_contexts(environment=environment)
        crypto_source = "hyperliquid_meta_and_asset_contexts"
    except Exception as exc:
        errors["crypto"] = str(exc)
        crypto_markets = []
        crypto_source = "unavailable"

    try:
        hip3_markets = _fetch_meta_and_asset_contexts(environment=environment, dex=hip3_dex)
        hip3_source = f"hyperliquid_meta_and_asset_contexts:{hip3_dex}"
    except Exception as exc:
        errors["hip3"] = str(exc)
        hip3_markets = _fallback_hip3_markets(hip3_dex)
        hip3_source = "available_symbol_cache" if hip3_markets else "unavailable"

    crypto_markets = crypto_markets[:limit]
    hip3_markets = hip3_markets[:limit]
    payload = {
        "venue": "hyperliquid",
        "environment": environment,
        "hip3_dex": hip3_dex,
        "updated_at": now,
        "source": {
            "crypto": crypto_source,
            "hip3": hip3_source,
        },
        "counts": {
            "crypto": len(crypto_markets),
            "hip3": len(hip3_markets),
            "total": len(crypto_markets) + len(hip3_markets),
        },
        "presets": {
            "crypto_top_20": _preset(crypto_markets, 20, limit),
            "crypto_top_50": _preset(crypto_markets, 50, limit),
            "hip3_top_20": _preset(hip3_markets, 20, limit),
            "hip3_top_50": _preset(hip3_markets, 50, limit),
        },
        "markets": {
            "crypto": crypto_markets,
            "hip3": hip3_markets,
        },
        "errors": errors,
    }
    _market_universe_cache[cache_key] = {
        "cached_at": now,
        "payload": payload,
    }
    return payload
