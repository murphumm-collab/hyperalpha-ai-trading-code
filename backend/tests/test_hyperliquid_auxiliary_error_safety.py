import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api import hyperliquid_routes


class FailingDbStub:
    def query(self, *args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    def rollback(self):
        pass


def _user(user_id: int = 7):
    return SimpleNamespace(id=user_id)


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered


def test_get_trading_mode_failure_uses_fixed_public_detail() -> None:
    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.get_trading_mode(
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_TRADING_MODE_READ_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_set_trading_mode_failure_uses_fixed_public_detail() -> None:
    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.set_trading_mode(
            request=hyperliquid_routes.TradingModeRequest(mode="mainnet"),
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_TRADING_MODE_UPDATE_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_get_all_wallets_failure_uses_fixed_public_detail() -> None:
    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.get_all_wallets(
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_WALLET_LIST_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_hyperliquid_auxiliary_error_safety_source_guard() -> None:
    with open(hyperliquid_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    auxiliary_block = source[
        source.index("# ========== Global Trading Mode Management =========="):
        source.index("# ============================================================================\n# Agent Wallet Endpoints")
    ]

    forbidden = (
        'logger.error(f"Failed to get trading mode: {e}"',
        'logger.error(f"Failed to set trading mode: {e}"',
        'logger.error(f"Failed to get all wallets: {e}"',
        'detail=f"Failed to get trading mode: {str(e)}"',
        'detail=f"Failed to set trading mode: {str(e)}"',
        'detail=f"Failed to get wallets: {str(e)}"',
        "detail=str(e)",
    )
    for pattern in forbidden:
        assert pattern not in auxiliary_block

    assert "SAFE_HYPERLIQUID_TRADING_MODE_READ_FAILED_MESSAGE" in auxiliary_block
    assert "SAFE_HYPERLIQUID_TRADING_MODE_UPDATE_FAILED_MESSAGE" in auxiliary_block
    assert "SAFE_HYPERLIQUID_WALLET_LIST_FAILED_MESSAGE" in auxiliary_block
