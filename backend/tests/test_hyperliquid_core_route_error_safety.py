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


def _setup_request():
    return hyperliquid_routes.HyperliquidSetupRequest(
        environment="testnet",
        privateKey="0x" + "1" * 64,
        maxLeverage=3,
        defaultLeverage=1,
    )


def _switch_request():
    return hyperliquid_routes.EnvironmentSwitchRequest(
        target_environment="mainnet",
        confirm_switch=True,
    )


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


def test_setup_account_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_setup(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "setup_hyperliquid_account", value_error_setup)

    with pytest.raises(HTTPException) as invalid_exc:
        hyperliquid_routes.setup_account(
            account_id=123,
            request=_setup_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert invalid_exc.value.status_code == 400
    assert invalid_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SETUP_INVALID_REQUEST_MESSAGE
    _assert_no_secret_echo({"detail": invalid_exc.value.detail})

    def runtime_setup(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "setup_hyperliquid_account", runtime_setup)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.setup_account(
            account_id=123,
            request=_setup_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SETUP_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_switch_environment_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_switch(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "switch_hyperliquid_environment", value_error_switch)

    with pytest.raises(HTTPException) as invalid_exc:
        hyperliquid_routes.switch_environment(
            account_id=123,
            request=_switch_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert invalid_exc.value.status_code == 400
    assert invalid_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SWITCH_INVALID_REQUEST_MESSAGE
    _assert_no_secret_echo({"detail": invalid_exc.value.detail})

    def runtime_switch(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "switch_hyperliquid_environment", runtime_switch)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.switch_environment(
            account_id=123,
            request=_switch_request(),
            db=DbStub(),
            current_user=_user(),
        )

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_SWITCH_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_get_config_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_config(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "get_account_hyperliquid_config", value_error_config)

    with pytest.raises(HTTPException) as not_found_exc:
        hyperliquid_routes.get_config(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert not_found_exc.value.status_code == 404
    assert not_found_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_CONFIG_NOT_FOUND_MESSAGE
    _assert_no_secret_echo({"detail": not_found_exc.value.detail})

    def runtime_config(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_account_hyperliquid_config", runtime_config)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.get_config(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_CONFIG_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_get_balance_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_client(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", value_error_client)

    with pytest.raises(HTTPException) as unavailable_exc:
        hyperliquid_routes.get_balance(
            account_id=123,
            force_refresh=True,
            environment="testnet",
            db=DbStub(),
            current_user=_user(),
        )

    assert unavailable_exc.value.status_code == 400
    assert unavailable_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_BALANCE_UNAVAILABLE_MESSAGE
    _assert_no_secret_echo({"detail": unavailable_exc.value.detail})

    def runtime_client(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", runtime_client)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.get_balance(
            account_id=123,
            force_refresh=True,
            environment="testnet",
            db=DbStub(),
            current_user=_user(),
        )

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_BALANCE_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_get_positions_failures_use_fixed_public_details(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    def value_error_client(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", value_error_client)

    with pytest.raises(HTTPException) as unavailable_exc:
        hyperliquid_routes.get_positions(
            account_id=123,
            force_refresh=True,
            environment="testnet",
            db=DbStub(),
            current_user=_user(),
        )

    assert unavailable_exc.value.status_code == 400
    assert unavailable_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_POSITIONS_UNAVAILABLE_MESSAGE
    _assert_no_secret_echo({"detail": unavailable_exc.value.detail})

    def runtime_client(*args, **kwargs):
        raise _private_error()

    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", runtime_client)

    with pytest.raises(HTTPException) as failure_exc:
        hyperliquid_routes.get_positions(
            account_id=123,
            force_refresh=True,
            environment="testnet",
            db=DbStub(),
            current_user=_user(),
        )

    assert failure_exc.value.status_code == 500
    assert failure_exc.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_POSITIONS_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": failure_exc.value.detail})


def test_hyperliquid_core_route_error_safety_source_guard() -> None:
    with open(hyperliquid_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    core_block = source[
        source.index('@router.post("/accounts/{account_id}/setup")'):
        source.index('@router.post("/accounts/{account_id}/orders/manual")')
    ]

    forbidden = (
        'logger.error(f"Setup failed: {e}"',
        'logger.error(f"Environment switch failed: {e}"',
        'logger.error(f"Failed to get config: {e}"',
        'logger.error(f"Failed to get balance: {e}"',
        'logger.error(f"Failed to get positions: {e}"',
        'detail=f"Setup failed: {str(e)}"',
        'detail=f"Switch failed: {str(e)}"',
        'detail=f"Balance query failed: {str(e)}"',
        'detail=f"Positions query failed: {str(e)}"',
        "detail=str(e)",
        "exc_info=True",
    )
    for pattern in forbidden:
        assert pattern not in core_block

    required = (
        "SAFE_HYPERLIQUID_SETUP_INVALID_REQUEST_MESSAGE",
        "SAFE_HYPERLIQUID_SETUP_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_SWITCH_INVALID_REQUEST_MESSAGE",
        "SAFE_HYPERLIQUID_SWITCH_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_CONFIG_NOT_FOUND_MESSAGE",
        "SAFE_HYPERLIQUID_CONFIG_READ_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_BALANCE_UNAVAILABLE_MESSAGE",
        "SAFE_HYPERLIQUID_BALANCE_READ_FAILED_MESSAGE",
        "SAFE_HYPERLIQUID_POSITIONS_UNAVAILABLE_MESSAGE",
        "SAFE_HYPERLIQUID_POSITIONS_READ_FAILED_MESSAGE",
    )
    for marker in required:
        assert marker in core_block
