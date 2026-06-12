import json
from types import SimpleNamespace

import pytest
import requests
from fastapi import HTTPException

from api import account_routes
from services import hyperliquid_environment


class ResponseStub:
    def __init__(self, status_code: int, body=None, json_error: Exception | None = None):
        self.status_code = status_code
        self._body = body
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._body


class QueryStub:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []


class DbStub:
    def query(self, *args, **kwargs):
        return QueryStub()


class FailingDbStub:
    def query(self, *args, **kwargs):
        raise RuntimeError("api_key=secret Bearer token=secret https://orders.internal")


def _user(user_id: int = 7):
    return SimpleNamespace(id=user_id)


def _account(account_id: int = 123):
    return SimpleNamespace(
        id=account_id,
        user_id=7,
        name="Trader",
        hyperliquid_mainnet_private_key="encrypted-mainnet-key",
    )


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered
    assert "provider.example" not in rendered


def test_builder_authorization_network_error_uses_fixed_public_detail(monkeypatch) -> None:
    def failing_post(*args, **kwargs):
        raise requests.RequestException(
            "api_key=secret Bearer token=secret https://provider.example/info"
        )

    monkeypatch.setattr(requests, "post", failing_post)

    with pytest.raises(HTTPException) as exc_info:
        account_routes.check_builder_authorization(
            wallet_address="0xabc",
            current_user=_user(),
            db=DbStub(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == account_routes.SAFE_BUILDER_AUTHORIZATION_CHECK_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_builder_authorization_invalid_body_uses_fixed_public_detail(monkeypatch) -> None:
    def invalid_json_post(*args, **kwargs):
        return ResponseStub(
            200,
            json_error=ValueError("api_key=secret Bearer token=secret https://provider.example/info"),
        )

    monkeypatch.setattr(requests, "post", invalid_json_post)

    with pytest.raises(HTTPException) as exc_info:
        account_routes.check_builder_authorization(
            wallet_address="0xabc",
            current_user=_user(),
            db=DbStub(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == account_routes.SAFE_BUILDER_AUTHORIZATION_CHECK_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_approve_builder_failure_does_not_echo_sdk_result(monkeypatch) -> None:
    class ExchangeStub:
        def approve_builder_fee(self, *args, **kwargs):
            return {
                "status": "err",
                "response": "api_key=secret Bearer token=secret https://orders.internal",
            }

    class ClientStub:
        sdk_exchange = ExchangeStub()

    monkeypatch.setattr(account_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(
        hyperliquid_environment,
        "get_hyperliquid_client",
        lambda *args, **kwargs: ClientStub(),
    )

    result = account_routes.approve_builder_fee(
        account_id=123,
        db=DbStub(),
        current_user=_user(),
    )

    assert result["success"] is False
    assert result["message"] == account_routes.SAFE_BUILDER_AUTHORIZATION_FAILED_MESSAGE
    assert result["result"] == {"status": "err"}
    _assert_no_secret_echo(result)


def test_approve_builder_exception_uses_fixed_public_detail(monkeypatch) -> None:
    def failing_client(*args, **kwargs):
        raise RuntimeError("api_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(account_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(hyperliquid_environment, "get_hyperliquid_client", failing_client)

    with pytest.raises(HTTPException) as exc_info:
        account_routes.approve_builder_fee(
            account_id=123,
            db=DbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == account_routes.SAFE_BUILDER_APPROVAL_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_check_mainnet_accounts_outer_failure_uses_fixed_public_detail() -> None:
    with pytest.raises(HTTPException) as exc_info:
        account_routes.check_mainnet_accounts(
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == account_routes.SAFE_BUILDER_MAINNET_CHECK_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_account_builder_error_safety_source_guard() -> None:
    with open(account_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    builder_block = source[
        source.index("def check_builder_authorization"):
        source.index('@router.post("/hyperliquid/approve-builder")')
    ]
    approve_block = source[
        source.index("def approve_builder_fee"):
        source.index('@router.get("/hyperliquid/check-mainnet-accounts")')
    ]
    mainnet_block = source[
        source.index("def check_mainnet_accounts"):
        source.index('@router.post("/{account_id}/disable-trading")')
    ]
    combined = "\n".join([builder_block, approve_block, mainnet_block])

    forbidden = (
        'detail=f"Network error: {str(e)}"',
        'detail=f"Failed to check authorization: {str(e)}"',
        'detail=f"Failed to approve builder fee: {str(e)}"',
        'detail=f"Failed to check mainnet accounts: {str(e)}"',
        "Network error checking builder authorization: {e}",
        "Error checking builder authorization: {e}",
        "EXCEPTION for account {account_id}: {type(e).__name__}: {e}",
        "Failed to approve builder fee for account {account_id}: {e}",
        "Error checking account {account.id} from wallets table: {account_err}",
        "Error checking account {account.id}: {account_err}",
        "Failed to check mainnet accounts: {e}",
        "result={result}",
        "result\": result",
        "result': result",
        "result.get('response'",
    )
    for pattern in forbidden:
        assert pattern not in combined

    assert "SAFE_BUILDER_AUTHORIZATION_CHECK_FAILED_MESSAGE" in combined
    assert "SAFE_BUILDER_APPROVAL_FAILED_MESSAGE" in combined
    assert "SAFE_BUILDER_MAINNET_CHECK_FAILED_MESSAGE" in combined
