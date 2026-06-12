import json
from types import SimpleNamespace

from services import hyper_ai_tools


def _render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _assert_no_secret_echo(payload: dict) -> None:
    rendered = _render(payload).lower()
    assert "postgres://" not in rendered
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "token" not in rendered
    assert "apikeysecreterror" not in rendered
    assert "_error_class" not in payload


class ApiKeySecretError(Exception):
    pass


def test_dispatcher_redacts_tool_exception_text_and_type(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise ApiKeySecretError(
            "postgres://user:pass@db/app?api_key=abc Bearer token private_key=xyz"
        )

    monkeypatch.setattr(hyper_ai_tools, "execute_get_watchlist", boom)

    payload = json.loads(
        hyper_ai_tools.execute_hyper_ai_tool(
            SimpleNamespace(),
            "get_watchlist",
            {},
            user_id=7,
        )
    )

    assert payload == {
        "error": "Hyper AI tool failed.",
        "error_code": "hyper_ai_tool_failed",
        "tool": "get_watchlist",
    }
    _assert_no_secret_echo(payload)


def test_direct_tool_redacts_service_exception_text(monkeypatch) -> None:
    from services import hyperliquid_symbol_service

    def boom(*args, **kwargs):
        raise RuntimeError(
            "https://orders.example/api?token=abc api_key=abc private_key=xyz"
        )

    monkeypatch.setattr(hyperliquid_symbol_service, "get_selected_symbols", boom)

    payload = json.loads(
        hyper_ai_tools.execute_get_watchlist(SimpleNamespace(), user_id=7)
    )

    assert payload == {
        "error": "Hyper AI tool failed.",
        "error_code": "hyper_ai_tool_failed",
        "tool": "get_watchlist",
    }
    _assert_no_secret_echo(payload)


def test_wallet_item_errors_do_not_echo_exchange_exception(monkeypatch) -> None:
    class QueryStub:
        def join(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            wallet = SimpleNamespace(
                environment="mainnet",
                wallet_address="0x1234567890abcdef1234",
            )
            account = SimpleNamespace(id=42, name="Primary")
            return [(wallet, account)]

    class DbStub:
        def query(self, *args, **kwargs):
            return QueryStub()

    def failing_client(*args, **kwargs):
        raise RuntimeError("Bearer token api_key=abc secret postgres://db")

    monkeypatch.setattr(hyper_ai_tools, "get_hyperliquid_client", failing_client, raising=False)

    import services.hyperliquid_environment as hyperliquid_environment

    monkeypatch.setattr(hyperliquid_environment, "get_hyperliquid_client", failing_client)

    payload = json.loads(
        hyper_ai_tools.execute_get_wallet_status(
            DbStub(),
            exchange="hyperliquid",
            environment="mainnet",
            user_id=7,
        )
    )

    assert payload["wallets"][0]["error"] == "Hyper AI tool item failed."
    assert payload["wallets"][0]["error_code"] == "hyper_ai_tool_item_failed"
    _assert_no_secret_echo(payload)


def test_hyper_ai_tool_error_source_guard() -> None:
    source = hyper_ai_tools.__file__
    with open(source, "r", encoding="utf-8") as handle:
        text = handle.read()

    forbidden = (
        'return json.dumps({"error": str(e)})',
        '"error": str(e)',
        '"_error_class": type(e).__name__',
        "Search failed: {err}",
        "Failed to fetch content from {url}",
        'test_result.get("message"',
        "e.detail",
    )
    for pattern in forbidden:
        assert pattern not in text

    assert "_safe_tool_error_payload" in text
    assert "SAFE_HYPER_AI_TOOL_ERROR_MESSAGE" in text
