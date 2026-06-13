import ast
import json
from pathlib import Path

from services import ai_trading_market_universe_service as market_universe_service


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "authorization" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "auth.internal" not in rendered
    assert "raw provider" not in rendered


class _ResponseStub:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _meta_payload(symbol: str, volume: str = "1000"):
    return [
        {"universe": [{"name": symbol, "maxLeverage": 5}]},
        [{"dayNtlVlm": volume, "markPx": "100", "openInterest": "10"}],
    ]


def _private_error() -> RuntimeError:
    return RuntimeError(
        "raw provider failure Bearer token=secret private_key=secret "
        "https://auth.internal/hyperliquid/meta"
    )


def test_market_universe_crypto_fetch_failure_uses_no_redirects_and_safe_error(monkeypatch):
    market_universe_service.clear_ai_trading_market_universe_cache()
    requests_seen = []

    def fake_post(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        payload = kwargs.get("json") or {}
        if "dex" not in payload:
            raise _private_error()
        return _ResponseStub(_meta_payload("NVDA", "900"))

    monkeypatch.setattr(market_universe_service.requests, "post", fake_post)

    result = market_universe_service.get_ai_trading_market_universe(
        environment="mainnet",
        limit=50,
        hip3_dex="xyz",
    )

    assert len(requests_seen) == 2
    assert all(call["kwargs"]["allow_redirects"] is False for call in requests_seen)
    assert result["source"]["crypto"] == "unavailable"
    assert result["source"]["hip3"] == "hyperliquid_meta_and_asset_contexts:xyz"
    assert result["errors"] == {
        "crypto": market_universe_service.SAFE_MARKET_UNIVERSE_PROVIDER_ERRORS["crypto"]
    }
    assert result["counts"]["hip3"] == 1
    _assert_no_secret_echo(result)


def test_market_universe_hip3_fallback_error_is_sanitized(monkeypatch):
    market_universe_service.clear_ai_trading_market_universe_cache()
    requests_seen = []

    def fake_post(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        payload = kwargs.get("json") or {}
        if payload.get("dex") == "xyz":
            raise _private_error()
        return _ResponseStub(_meta_payload("BTC"))

    monkeypatch.setattr(market_universe_service.requests, "post", fake_post)
    monkeypatch.setattr(
        market_universe_service,
        "get_available_symbols",
        lambda: [{"type": "hip3", "name": "NVDA", "maxLeverage": 3}],
    )

    result = market_universe_service.get_ai_trading_market_universe(
        environment="mainnet",
        limit=50,
        hip3_dex="xyz",
    )

    assert len(requests_seen) == 2
    assert all(call["kwargs"]["allow_redirects"] is False for call in requests_seen)
    assert result["source"]["crypto"] == "hyperliquid_meta_and_asset_contexts"
    assert result["source"]["hip3"] == "available_symbol_cache"
    assert result["errors"] == {
        "hip3": market_universe_service.SAFE_MARKET_UNIVERSE_PROVIDER_ERRORS["hip3"]
    }
    assert result["presets"]["hip3_top_20"][0]["exchange_symbol"] == "xyz:NVDA"
    _assert_no_secret_echo(result)


def test_market_universe_error_safety_source_guard() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "ai_trading_market_universe_service.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    post_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "post"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "requests"
    ]
    assert post_calls
    for call in post_calls:
        keyword_values = {
            keyword.arg: keyword.value
            for keyword in call.keywords
            if keyword.arg is not None
        }
        assert "allow_redirects" in keyword_values
        assert isinstance(keyword_values["allow_redirects"], ast.Constant)
        assert keyword_values["allow_redirects"].value is False

    assert "errors[\"crypto\"] = str(exc)" not in source
    assert "errors[\"hip3\"] = str(exc)" not in source
    assert "errors['crypto'] = str(exc)" not in source
    assert "errors['hip3'] = str(exc)" not in source
    assert "SAFE_MARKET_UNIVERSE_PROVIDER_ERRORS" in source
