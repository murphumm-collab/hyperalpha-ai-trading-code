import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api import hyperliquid_routes


class DbStub:
    pass


class FailingSnapshotDbStub:
    def query(self, *args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    def close(self):
        pass


def _user(user_id: int = 7):
    return SimpleNamespace(id=user_id)


def _account(account_id: int = 123):
    return SimpleNamespace(id=account_id, user_id=7, name="Trader", hyperliquid_environment="testnet")


def _private_error():
    return RuntimeError("private_key=secret Bearer token=secret https://orders.internal")


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered


def test_account_snapshots_failure_uses_fixed_public_detail(monkeypatch) -> None:
    import database.snapshot_connection

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(database.snapshot_connection, "SnapshotSessionLocal", lambda: FailingSnapshotDbStub())

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.get_account_snapshots(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SNAPSHOT_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_symbol_read_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "get_available_symbols_info", lambda: (_ for _ in ()).throw(_private_error()))

    with pytest.raises(HTTPException) as available_exc:
        hyperliquid_routes.list_available_symbols()

    assert available_exc.value.status_code == 500
    assert available_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SYMBOL_LIST_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": available_exc.value.detail})

    def failing_ranked_symbols(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_ranked_symbols", failing_ranked_symbols)

    with pytest.raises(HTTPException) as ranked_exc:
        hyperliquid_routes.list_ranked_symbols(limit=20, environment="mainnet")

    assert ranked_exc.value.status_code == 500
    assert ranked_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SYMBOL_RANKING_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": ranked_exc.value.detail})


def test_watchlist_read_and_update_failures_use_fixed_public_details(monkeypatch) -> None:
    def failing_get_selected_symbols(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_selected_symbols", failing_get_selected_symbols)

    with pytest.raises(HTTPException) as read_exc:
        hyperliquid_routes.get_symbol_watchlist(current_user=_user())

    assert read_exc.value.status_code == 500
    assert read_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WATCHLIST_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": read_exc.value.detail})

    def value_error_update(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "update_selected_symbols", value_error_update)
    payload = hyperliquid_routes.HyperliquidSymbolSelectionRequest(symbols=["BTC"])

    with pytest.raises(HTTPException) as invalid_exc:
        hyperliquid_routes.update_symbol_watchlist(payload=payload, current_user=_user())

    assert invalid_exc.value.status_code == 400
    assert invalid_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WATCHLIST_UPDATE_INVALID_REQUEST_MESSAGE
    _assert_no_secret_echo({"detail": invalid_exc.value.detail})

    def runtime_update(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "update_selected_symbols", runtime_update)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.update_symbol_watchlist(payload=payload, current_user=_user())

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WATCHLIST_UPDATE_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_action_summary_failure_uses_fixed_public_detail(monkeypatch) -> None:
    def failing_account_ids(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "_current_user_account_ids", failing_account_ids)

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.get_action_summary(
            db=DbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_ACTION_SUMMARY_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_hyperliquid_read_route_error_safety_source_guard() -> None:
    with open(hyperliquid_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    read_block = source[
        source.index('@router.get("/accounts/{account_id}/snapshots")'):
        source.index('@router.get("/accounts/{account_id}/rate-limit")')
    ]

    forbidden = (
        'logger.error(f"Failed to update Hyperliquid watchlist: {err}"',
        'logger.error(f"Failed to summarize Hyperliquid actions: {err}"',
        'logger.info(f"[Hyperliquid] Watchlist updated',
        "detail=str(err)",
        "detail=str(e)",
        "str(err)",
        "str(e)",
        "exc_info=True",
    )
    for pattern in forbidden:
        assert pattern not in read_block

    required = (
        "SAFE_HYPERLIQUID_SNAPSHOT_READ_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_SYMBOL_LIST_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_SYMBOL_RANKING_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_WATCHLIST_READ_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_WATCHLIST_UPDATE_INVALID_REQUEST_MESSAGE",
        "SAFE_HYPERLIQUID_WATCHLIST_UPDATE_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_ACTION_SUMMARY_READ_FAILED_MESSAGE",
    )
    for marker in required:
        assert marker in read_block
