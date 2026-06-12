import asyncio
import logging
from datetime import datetime

from services.kline_collectors import HyperliquidKlineCollector


class _FakeMarketData:
    def __init__(self, payloads):
        self.payloads = payloads

    def get_kline_data(self, symbol, period, count):
        return self.payloads


def _collector(payloads) -> HyperliquidKlineCollector:
    collector = HyperliquidKlineCollector.__new__(HyperliquidKlineCollector)
    collector.exchange_id = "hyperliquid"
    collector.logger = logging.getLogger("test.hyperliquid_kline_collector")
    collector.market_data = _FakeMarketData(payloads)
    return collector


def test_hyperliquid_collector_uses_latest_native_candle_and_normalizes_ms_timestamp():
    collector = _collector([
        {"t": 1_780_000_000_000, "o": "100", "h": "110", "l": "95", "c": "105", "v": "12"},
        {"t": 1_780_000_060_000, "o": "106", "h": "116", "l": "101", "c": "111", "v": "15.5"},
    ])

    result = asyncio.run(collector.fetch_current_kline("xyz:NVDA", "1m"))

    assert result is not None
    assert result.exchange == "hyperliquid"
    assert result.symbol == "xyz:NVDA"
    assert result.period == "1m"
    assert result.timestamp == 1_780_000_060
    assert result.open_price == 106.0
    assert result.close_price == 111.0
    assert result.volume == 15.5


def test_hyperliquid_collector_skips_malformed_candles_in_history():
    collector = _collector([
        {"timestamp": 100, "open": "bad", "high": 110, "low": 95, "close": 105, "volume": 12},
        {"timestamp": 120, "open": 100, "high": 110, "low": 95, "close": 105, "volume": 12},
        {"timestamp": 180_000, "open": 106, "high": 116, "low": 101, "close": 111, "volume": 15},
    ])

    result = asyncio.run(collector.fetch_historical_klines(
        "BTC",
        datetime.fromtimestamp(90),
        datetime.fromtimestamp(130),
        "1m",
    ))

    assert len(result) == 1
    assert result[0].timestamp == 120
    assert result[0].close_price == 105.0


def test_hyperliquid_collector_returns_none_for_secret_like_malformed_current_payload():
    collector = _collector([
        {"timestamp": 100, "open": "api_key=secret", "high": 110, "low": 95, "close": 105, "volume": 12},
    ])

    result = asyncio.run(collector.fetch_current_kline("BTC", "1m"))

    assert result is None
