import json

from services import hyperliquid_symbol_service


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered


def _private_error():
    return RuntimeError("private_key=secret Bearer token=secret https://orders.internal")


def test_ranked_symbol_fallback_uses_fixed_public_error(monkeypatch) -> None:
    def failing_post(*args, **kwargs):
        raise _private_error()

    requests_seen = []

    def recording_failing_post(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        raise _private_error()

    monkeypatch.setattr(hyperliquid_symbol_service.requests, "post", recording_failing_post)
    monkeypatch.setattr(
        hyperliquid_symbol_service,
        "get_available_symbols",
        lambda: [{"symbol": "BTC", "name": "Bitcoin", "type": "perp"}],
    )
    hyperliquid_symbol_service._ranked_symbol_cache.update(
        {"environment": None, "updated_at": 0.0, "symbols": [], "source": None}
    )

    result = hyperliquid_symbol_service.get_ranked_symbols(limit=10, environment="mainnet")

    assert result["source"] == "available_symbol_cache"
    assert result["error"] == hyperliquid_symbol_service.SAFE_HYPERLIQUID_RANKED_SYMBOLS_ERROR_MESSAGE
    assert result["symbols"][0]["symbol"] == "BTC"
    assert requests_seen
    assert requests_seen[0]["kwargs"]["allow_redirects"] is False
    _assert_no_secret_echo(result)


def test_fetch_remote_symbols_uses_no_redirects_and_no_public_error_payload(monkeypatch) -> None:
    requests_seen = []

    def failing_post(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        raise _private_error()

    monkeypatch.setattr(hyperliquid_symbol_service.requests, "post", failing_post)

    result = hyperliquid_symbol_service.fetch_remote_symbols(environment="testnet")

    assert result == []
    assert requests_seen
    assert requests_seen[0]["kwargs"]["allow_redirects"] is False
    _assert_no_secret_echo({"symbols": result})


def test_fetch_remote_symbols_hip3_branch_disables_redirects(monkeypatch) -> None:
    class ResponseStub:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    requests_seen = []

    def post_stub(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        if len(requests_seen) == 1:
            return ResponseStub({"universe": [{"name": "BTC", "isDelisted": False}]})
        return ResponseStub({"universe": []})

    monkeypatch.setattr(hyperliquid_symbol_service.requests, "post", post_stub)

    result = hyperliquid_symbol_service.fetch_remote_symbols(environment="mainnet")

    assert result[0]["symbol"] == "BTC"
    assert len(requests_seen) == 2
    assert all(call["kwargs"]["allow_redirects"] is False for call in requests_seen)


def test_hyperliquid_symbol_service_error_safety_source_guard() -> None:
    with open(hyperliquid_symbol_service.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    forbidden = (
        '"error": str(err)',
        "logger.warning(\"Failed to fetch Hyperliquid meta info: %s\", err)",
        "logger.warning(\"Failed to fetch HIP-3 symbols: %s\", err)",
        "logger.warning(\"Failed to fetch Hyperliquid ranked symbols: %s\", err)",
        "logger.warning(\"Hyperliquid symbol refresh failed: %s\", err)",
        "logger.warning(\"Unable to update market stream symbols: %s\", err)",
        "logger.warning(\"Unable to update market flow collector: %s\", err)",
        "logger.info(\"Hyperliquid watchlist updated for %s: %s\"",
    )
    for pattern in forbidden:
        assert pattern not in source

    assert "SAFE_HYPERLIQUID_RANKED_SYMBOLS_ERROR_MESSAGE" in source
    assert "SAFE_HYPERLIQUID_SYMBOL_REFRESH_FAILED_MESSAGE" in source
    assert "SAFE_HYPERLIQUID_STREAM_SYMBOL_REFRESH_FAILED_MESSAGE" in source
    assert "allow_redirects=False" in source
