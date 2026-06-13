import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api import hyperliquid_routes


class DbStub:
    pass


def _user(user_id: int = 7):
    return SimpleNamespace(id=user_id)


def _account(account_id: int = 123):
    return SimpleNamespace(id=account_id, user_id=7, name="Trader")


def _manual_order_request():
    return hyperliquid_routes.ManualOrderRequest(
        symbol="BTC",
        is_buy=True,
        size=0.01,
        price=50000,
        leverage=2,
        environment="testnet",
    )


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


def test_manual_order_preserves_http_exceptions(monkeypatch) -> None:
    def missing_owner(*args, **kwargs):
        raise HTTPException(status_code=404, detail="Account 123 not found")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", missing_owner)

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.place_manual_order(
            account_id=123,
            request=_manual_order_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Account 123 not found"


def test_manual_order_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_client(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", value_error_client)

    with pytest.raises(HTTPException) as invalid_exc:
        hyperliquid_routes.place_manual_order(
            account_id=123,
            request=_manual_order_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert invalid_exc.value.status_code == 400
    assert invalid_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_ORDER_INVALID_REQUEST_MESSAGE
    _assert_no_secret_echo({"detail": invalid_exc.value.detail})

    def runtime_client(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", runtime_client)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.place_manual_order(
            account_id=123,
            request=_manual_order_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_ORDER_PLACEMENT_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_disable_and_enable_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def disable_value_error(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "disable_hyperliquid_trading", disable_value_error)

    with pytest.raises(HTTPException) as disable_invalid_exc:
        hyperliquid_routes.disable_trading(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert disable_invalid_exc.value.status_code == 400
    assert disable_invalid_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_DISABLE_INVALID_REQUEST_MESSAGE
    _assert_no_secret_echo({"detail": disable_invalid_exc.value.detail})

    def disable_runtime_error(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "disable_hyperliquid_trading", disable_runtime_error)

    with pytest.raises(HTTPException) as disable_failure_exc:
        hyperliquid_routes.disable_trading(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert disable_failure_exc.value.status_code == 500
    assert disable_failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_DISABLE_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": disable_failure_exc.value.detail})

    def enable_value_error(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "enable_hyperliquid_trading", enable_value_error)

    with pytest.raises(HTTPException) as enable_invalid_exc:
        hyperliquid_routes.enable_trading(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert enable_invalid_exc.value.status_code == 400
    assert enable_invalid_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_ENABLE_INVALID_REQUEST_MESSAGE
    _assert_no_secret_echo({"detail": enable_invalid_exc.value.detail})

    def enable_runtime_error(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "enable_hyperliquid_trading", enable_runtime_error)

    with pytest.raises(HTTPException) as enable_failure_exc:
        hyperliquid_routes.enable_trading(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert enable_failure_exc.value.status_code == 500
    assert enable_failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_ENABLE_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": enable_failure_exc.value.detail})


def test_connection_test_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_client(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", value_error_client)

    with pytest.raises(HTTPException) as unavailable_exc:
        hyperliquid_routes.test_connection(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert unavailable_exc.value.status_code == 400
    assert unavailable_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_CONNECTION_TEST_UNAVAILABLE_MESSAGE
    _assert_no_secret_echo({"detail": unavailable_exc.value.detail})

    def runtime_client(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", runtime_client)

    result = hyperliquid_routes.test_connection(
        account_id=123,
        db=DbStub(),
        current_user=_user(),
    )

    assert result == {
        "connected": False,
        "error": hyperliquid_routes.SAFE_HYPERLIQUID_CONNECTION_TEST_FAILED_MESSAGE,
        "account_id": 123,
    }
    _assert_no_secret_echo(result)


def test_rate_limit_and_trading_stats_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def runtime_client(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", runtime_client)

    with pytest.raises(HTTPException) as rate_limit_exc:
        hyperliquid_routes.get_account_rate_limit(
            account_id=123,
            environment="testnet",
            db=DbStub(),
            current_user=_user(),
        )

    assert rate_limit_exc.value.status_code == 500
    assert rate_limit_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_RATE_LIMIT_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": rate_limit_exc.value.detail})

    with pytest.raises(HTTPException) as stats_exc:
        hyperliquid_routes.get_account_trading_stats(
            account_id=123,
            environment="testnet",
            db=DbStub(),
            current_user=_user(),
        )

    assert stats_exc.value.status_code == 500
    assert stats_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_TRADING_STATS_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": stats_exc.value.detail})


def test_hyperliquid_execution_route_error_safety_source_guard() -> None:
    with open(hyperliquid_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    execution_block = "\n".join(
        [
            source[
                source.index('@router.post("/accounts/{account_id}/orders/manual")'):
                source.index('@router.get("/accounts/{account_id}/snapshots")')
            ],
            source[
                source.index('@router.get("/accounts/{account_id}/rate-limit")'):
                source.index('@router.get("/health")')
            ],
        ]
    )

    forbidden = (
        'logger.error(f"Manual order failed: {e}"',
        'logger.error(f"Failed to disable trading: {e}"',
        'logger.error(f"Failed to enable trading: {e}"',
        'logger.error(f"Connection test failed: {e}"',
        'logger.error(f"Failed to get rate limit for account {account_id}: {e}"',
        'logger.error(f"Failed to get trading stats for account {account_id}: {e}"',
        'detail=f"Order placement failed: {str(e)}"',
        'detail=f"Failed to query rate limit: {str(e)}"',
        'detail=f"Failed to query trading stats: {str(e)}"',
        "'error': str(e)",
        "detail=str(e)",
        "exc_info=True",
    )
    for pattern in forbidden:
        assert pattern not in execution_block

    required = (
        "SAFE_HYPERLIQUID_ORDER_INVALID_REQUEST_MESSAGE",
        "SAFE_HYPERLIQUID_ORDER_PLACEMENT_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_DISABLE_INVALID_REQUEST_MESSAGE",
        "SAFE_HYPERLIQUID_DISABLE_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_ENABLE_INVALID_REQUEST_MESSAGE",
        "SAFE_HYPERLIQUID_ENABLE_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_CONNECTION_TEST_UNAVAILABLE_MESSAGE",
        "SAFE_HYPERLIQUID_CONNECTION_TEST_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_RATE_LIMIT_READ_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_TRADING_STATS_READ_FAILED_MESSAGE",
    )
    for marker in required:
        assert marker in execution_block
