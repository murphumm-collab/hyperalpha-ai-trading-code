import ast
import json
import logging
from pathlib import Path

import requests

from services import hyperliquid_market_data
from services.exchanges.symbol_mapper import SymbolMapper
from services import kline_collectors
from services.kline_collectors import HyperliquidKlineCollector


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered


def _private_error() -> RuntimeError:
    return RuntimeError("private_key=secret Bearer token=secret https://orders.internal")


def _client() -> hyperliquid_market_data.HyperliquidClient:
    client = hyperliquid_market_data.HyperliquidClient.__new__(
        hyperliquid_market_data.HyperliquidClient
    )
    client.environment = "mainnet"
    client.exchange = None
    return client


def test_ticker_native_request_disables_redirects_and_logs_safely(monkeypatch, caplog) -> None:
    client = _client()
    requests_seen = []

    def failing_post(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        raise _private_error()

    monkeypatch.setattr(requests, "post", failing_post)
    monkeypatch.setattr(
        client,
        "_get_ccxt_ticker_fallback",
        lambda symbol: {"symbol": symbol, "price": 0, "source": "fallback"},
    )
    caplog.set_level(logging.ERROR, logger=hyperliquid_market_data.logger.name)

    result = client.get_ticker_data("BTC")

    assert result == {"symbol": "BTC", "price": 0, "source": "fallback"}
    assert requests_seen
    assert requests_seen[0]["kwargs"]["allow_redirects"] is False
    _assert_no_secret_echo(result)
    _assert_no_secret_echo(caplog.text)


def test_market_status_returns_fixed_public_error_without_raw_exception(caplog) -> None:
    class FailingExchange:
        def load_markets(self):
            raise _private_error()

    client = _client()
    client.exchange = FailingExchange()
    caplog.set_level(logging.ERROR, logger=hyperliquid_market_data.logger.name)

    result = client.get_market_status("BTC")

    assert result == {
        "market_status": "ERROR",
        "is_trading": False,
        "error": hyperliquid_market_data.SAFE_HYPERLIQUID_MARKET_STATUS_ERROR_MESSAGE,
    }
    _assert_no_secret_echo(result)
    _assert_no_secret_echo(caplog.text)


def test_hip3_kline_request_disables_redirects_and_logs_safely(monkeypatch, caplog) -> None:
    client = _client()
    requests_seen = []

    def failing_post(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        raise _private_error()

    monkeypatch.setattr(requests, "post", failing_post)
    monkeypatch.setitem(SymbolMapper._hip3_mappings, "NVDA", "xyz:NVDA")
    caplog.set_level(logging.WARNING, logger=hyperliquid_market_data.logger.name)

    result = client._fetch_kline_native_range("NVDA", "1m", 1_700_000_000_000, 1_700_000_060_000)

    assert result == []
    assert requests_seen
    assert requests_seen[0]["kwargs"]["allow_redirects"] is False
    _assert_no_secret_echo(caplog.text)


def test_collector_supported_symbols_failure_logs_metadata_only(monkeypatch, caplog) -> None:
    from services import hyperliquid_symbol_service

    collector = HyperliquidKlineCollector.__new__(HyperliquidKlineCollector)
    collector.exchange_id = "hyperliquid"
    collector.logger = logging.getLogger("test.hyperliquid_kline_collector")
    collector.market_data = None
    def failing_get_selected_symbols():
        raise _private_error()

    monkeypatch.setattr(hyperliquid_symbol_service, "get_selected_symbols", failing_get_selected_symbols)
    caplog.set_level(logging.WARNING, logger=collector.logger.name)

    result = collector.get_supported_symbols()

    assert result == ["BTC"]
    _assert_no_secret_echo(caplog.text)


def test_hyperliquid_market_data_error_safety_source_guard() -> None:
    source_path = Path(hyperliquid_market_data.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden = (
        "logger.warning(f\"Failed to pre-load markets (will load on first use): {market_err}\")",
        "logger.error(f\"Failed to initialize Hyperliquid exchange for {self.environment}: {e}\")",
        "logger.error(f\"Error fetching price for {symbol}: {e}\")",
        "logger.error(f\"Error fetching Hyperliquid ticker for {symbol}: {e}\")",
        "logger.error(f\"CCXT fallback failed for {symbol}: {e}\")",
        "logger.warning(f\"Failed to persist kline data for {symbol}: {persist_error}\")",
        "logger.error(f\"Error fetching klines for {symbol}: {e}\")",
        "logger.error(f\"Error fetching historical klines for {symbol}: {e}\")",
        "logger.error(f\"Error persisting kline data: {e}\")",
        "logger.error(f\"Error getting market status for {symbol}: {e}\")",
        "'error': str(e)",
        "logger.error(f\"Error getting symbols: {e}\")",
        "requests.post(\"https://api.hyperliquid.xyz/info\", json=payload, timeout=15)",
        "logger.warning(\"Failed to fetch HIP-3 klines for %s: %s\", symbol, err)",
        "logger.warning(f\"Failed to persist HIP-3 kline data for {symbol}: {persist_error}\")",
    )
    for pattern in forbidden:
        assert pattern not in source

    request_posts = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "post"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "requests"
    ]
    assert request_posts
    for call in request_posts:
        allow_redirects = [
            keyword.value
            for keyword in call.keywords
            if keyword.arg == "allow_redirects"
        ]
        assert allow_redirects
        assert isinstance(allow_redirects[0], ast.Constant)
        assert allow_redirects[0].value is False

    collector_source = Path(kline_collectors.__file__).read_text(encoding="utf-8")

    assert "SAFE_HYPERLIQUID_MARKET_STATUS_ERROR_MESSAGE" in source
    assert "Failed to get symbols from hyperliquid_symbol_service" not in collector_source
    assert "Failed to get Hyperliquid selected symbols" in collector_source
    assert 'extra={"error_type": type(e).__name__}' in collector_source
    assert "allow_redirects=False" in source
    assert (
        "Hyperliquid market status is temporarily unavailable"
        in hyperliquid_market_data.SAFE_HYPERLIQUID_MARKET_STATUS_ERROR_MESSAGE
    )
