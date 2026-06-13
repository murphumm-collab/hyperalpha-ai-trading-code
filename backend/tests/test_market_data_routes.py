import asyncio
import json

from api import market_data_routes


def test_kline_with_indicators_failure_returns_safe_empty_series(monkeypatch):
    def failing_get_kline_data(*args, **kwargs):
        raise RuntimeError("api_key=secret token=secret private_key=secret")

    monkeypatch.setattr(market_data_routes, "get_kline_data", failing_get_kline_data)

    response = asyncio.run(
        market_data_routes.get_kline_with_indicators(
            symbol="BTC",
            market="hyperliquid",
            period="1m",
            count=500,
            indicators="MACD",
        )
    )

    payload = response.model_dump()
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert payload["count"] == 0
    assert payload["klines"] == []
    assert payload["indicators"] == {}
    assert "api_key" not in rendered
    assert "private_key" not in rendered
    assert "token" not in rendered
