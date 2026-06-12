import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api import hyperliquid_routes


class QueryStub:
    def __init__(self, first_value=None, all_value=None):
        self._first_value = first_value
        self._all_value = all_value if all_value is not None else []

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_value

    def all(self):
        return self._all_value


class FailingDbStub:
    def query(self, *args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")


class DeleteFailingDbStub:
    def query(self, *args, **kwargs):
        return QueryStub(first_value=SimpleNamespace(wallet_address="0x123"))

    def delete(self, *args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    def rollback(self):
        pass


class EmptyDbStub:
    def query(self, *args, **kwargs):
        return QueryStub()


def _user(user_id: int = 7):
    return SimpleNamespace(id=user_id)


def _account(account_id: int = 123):
    return SimpleNamespace(id=account_id, user_id=7, name="Trader")


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered


def test_configure_wallet_invalid_private_key_uses_fixed_public_detail(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    request = hyperliquid_routes.WalletConfigRequest(
        privateKey="g" * 64,
        environment="testnet",
    )

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.configure_account_wallet(
            account_id=123,
            request=request,
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_INVALID_PRIVATE_KEY_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_configure_wallet_unexpected_failure_uses_fixed_public_detail(monkeypatch) -> None:
    def failing_owner(*args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", failing_owner)

    request = hyperliquid_routes.WalletConfigRequest(
        privateKey="0x" + "1" * 64,
        environment="testnet",
    )

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.configure_account_wallet(
            account_id=123,
            request=request,
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_CONFIG_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_configure_wallet_encryption_failure_uses_fixed_public_detail(monkeypatch) -> None:
    import utils.encryption

    def failing_encrypt_private_key(*args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(utils.encryption, "encrypt_private_key", failing_encrypt_private_key)

    request = hyperliquid_routes.WalletConfigRequest(
        privateKey="0x" + "1" * 64,
        environment="testnet",
    )

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.configure_account_wallet(
            account_id=123,
            request=request,
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_CONFIG_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_get_wallet_config_failure_uses_fixed_public_detail() -> None:
    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.get_account_wallet(
            account_id=123,
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_delete_wallet_failure_uses_fixed_public_detail(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.delete_account_wallet(
            account_id=123,
            environment="mainnet",
            db=DeleteFailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_DELETE_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_wallet_connection_value_error_uses_fixed_public_detail(monkeypatch) -> None:
    def failing_client(*args, **kwargs):
        raise ValueError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", failing_client)

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.test_wallet_connection(
            account_id=123,
            body=hyperliquid_routes.TestWalletRequest(environment="mainnet"),
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_TEST_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_wallet_connection_generic_failure_uses_fixed_public_error(monkeypatch) -> None:
    class ClientStub:
        wallet_address = "0xabc"

        def get_account_state(self, db):
            raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(hyperliquid_routes, "get_hyperliquid_client", lambda *args, **kwargs: ClientStub())

    result = hyperliquid_routes.test_wallet_connection(
        account_id=123,
        body=hyperliquid_routes.TestWalletRequest(environment="mainnet"),
        db=EmptyDbStub(),
        current_user=_user(),
    )

    assert result["success"] is False
    assert result["connection"] == "failed"
    assert result["error"] == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_TEST_FAILED_MESSAGE
    _assert_no_secret_echo(result)


def test_hyperliquid_private_key_wallet_error_safety_source_guard() -> None:
    with open(hyperliquid_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    wallet_block = source[
        source.index("def get_account_wallet"):
        source.index("# ========== Global Trading Mode Management ==========")
    ]

    forbidden = (
        'detail=f"Failed to get wallet configuration: {str(e)}"',
        'detail=f"Invalid private key: {str(e)}"',
        'detail=f"Failed to configure wallet: {str(e)}"',
        'logger.error(f"Failed to encrypt private key: {e}")',
        'detail="Failed to encrypt private key"',
        'detail=f"Failed to delete wallet: {str(e)}"',
        'detail=f"Failed to test connection: {str(e)}"',
        "detail=str(e)",
        "'error': str(e)",
        "result={result}",
        "Authorization completed for account {account_id}: {result}",
        "Authorization FAILED for account {account_id}: {result}",
        "Authorization failed for account {account_id}: {type(e).__name__}: {e}",
    )
    for pattern in forbidden:
        assert pattern not in wallet_block

    assert "SAFE_HYPERLIQUID_WALLET_CONFIG_FAILED_MESSAGE" in wallet_block
    assert "SAFE_HYPERLIQUID_WALLET_TEST_FAILED_MESSAGE" in wallet_block
    assert "allow_redirects=False" in wallet_block
