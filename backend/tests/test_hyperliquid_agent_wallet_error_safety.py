import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import HTTPException

from api import hyperliquid_routes


class QueryStub:
    def __init__(self, first_value=None, all_value=None):
        self._first_value = first_value
        self._all_value = all_value if all_value is not None else []

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_value

    def all(self):
        return self._all_value


class WalletDbStub:
    def __init__(self, wallet=None):
        self.wallet = wallet

    def query(self, *args, **kwargs):
        return QueryStub(first_value=self.wallet)

    def commit(self):
        pass


class EmptyDbStub:
    def query(self, *args, **kwargs):
        return QueryStub()

    def add(self, *args, **kwargs):
        pass

    def flush(self):
        pass

    def commit(self):
        pass


class FailingDbStub:
    def query(self, *args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")


def _user(user_id: int = 7):
    return SimpleNamespace(id=user_id)


def _account(account_id: int = 123):
    return SimpleNamespace(id=account_id, user_id=7, name="Trader")


def _wallet():
    return SimpleNamespace(
        id=1,
        private_key_encrypted="encrypted",
        wallet_address="0x1111111111111111111111111111111111111111",
        environment="testnet",
        key_type="private_key",
        master_wallet_address=None,
        agent_valid_until=None,
        max_leverage=3,
        default_leverage=1,
        is_active="true",
    )


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "orders.internal" not in rendered


def _install_exchange_stub(monkeypatch, exchange_class) -> None:
    hyperliquid_module = ModuleType("hyperliquid")
    exchange_module = ModuleType("hyperliquid.exchange")
    exchange_module.Exchange = exchange_class
    hyperliquid_module.exchange = exchange_module
    monkeypatch.setitem(sys.modules, "hyperliquid", hyperliquid_module)
    monkeypatch.setitem(sys.modules, "hyperliquid.exchange", exchange_module)


def test_upgrade_agent_wallet_approve_error_uses_fixed_public_detail(monkeypatch) -> None:
    import utils.encryption

    class ExchangeStub:
        def __init__(self, *args, **kwargs):
            pass

        def approve_agent(self, *args, **kwargs):
            return (
                {
                    "status": "err",
                    "response": "private_key=secret Bearer token=secret https://orders.internal",
                },
                "0x" + "2" * 64,
            )

    _install_exchange_stub(monkeypatch, ExchangeStub)
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(utils.encryption, "decrypt_private_key", lambda *args, **kwargs: "0x" + "1" * 64)

    request = hyperliquid_routes.AgentWalletUpgradeRequest(environment="testnet", agentName="Agent")

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.upgrade_wallet_to_agent(
            account_id=123,
            request=request,
            db=WalletDbStub(wallet=_wallet()),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_AGENT_WALLET_APPROVAL_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_upgrade_agent_wallet_unexpected_failure_uses_fixed_public_detail(monkeypatch) -> None:
    def failing_owner(*args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", failing_owner)

    request = hyperliquid_routes.AgentWalletUpgradeRequest(environment="testnet", agentName="Agent")

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.upgrade_wallet_to_agent(
            account_id=123,
            request=request,
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_AGENT_WALLET_UPGRADE_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_configure_agent_wallet_invalid_key_uses_fixed_public_detail(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    request = hyperliquid_routes.AgentWalletConfigRequest(
        agentPrivateKey="g" * 64,
        masterWalletAddress="0x" + "1" * 40,
        environment="testnet",
    )

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.configure_agent_wallet(
            account_id=123,
            request=request,
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_AGENT_WALLET_INVALID_PRIVATE_KEY_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_configure_agent_wallet_encryption_failure_uses_fixed_public_detail(monkeypatch) -> None:
    import utils.encryption

    def failing_encrypt_private_key(*args, **kwargs):
        raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())
    monkeypatch.setattr(hyperliquid_routes, "_get_extra_agents", lambda *args, **kwargs: [])
    monkeypatch.setattr(utils.encryption, "encrypt_private_key", failing_encrypt_private_key)

    request = hyperliquid_routes.AgentWalletConfigRequest(
        agentPrivateKey="0x" + "2" * 64,
        masterWalletAddress="0x" + "1" * 40,
        environment="testnet",
    )

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.configure_agent_wallet(
            account_id=123,
            request=request,
            db=EmptyDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_AGENT_WALLET_CONFIG_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_agent_wallet_status_failure_uses_fixed_public_detail(monkeypatch) -> None:
    monkeypatch.setattr(hyperliquid_routes, "_ensure_account_owner", lambda *args, **kwargs: _account())

    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.get_agent_wallet_status(
            account_id=123,
            environment="mainnet",
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_AGENT_WALLET_STATUS_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_wallet_upgrade_check_failure_uses_fixed_public_detail() -> None:
    with pytest.raises(HTTPException) as exc_info:
        hyperliquid_routes.check_wallet_upgrade_needed(
            db=FailingDbStub(),
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == hyperliquid_routes.SAFE_HYPERLIQUID_AGENT_WALLET_UPGRADE_CHECK_FAILED_MESSAGE
    _assert_no_secret_echo({"detail": exc_info.value.detail})


def test_extra_agents_query_disables_redirects(monkeypatch) -> None:
    calls = []

    class ResponseStub:
        def raise_for_status(self):
            raise RuntimeError("private_key=secret Bearer token=secret https://orders.internal")

    def post_stub(*args, **kwargs):
        calls.append(kwargs)
        return ResponseStub()

    monkeypatch.setattr("requests.post", post_stub)

    result = hyperliquid_routes._get_extra_agents("https://api.hyperliquid.xyz", "0x" + "1" * 40)

    assert result == []
    assert calls
    assert calls[0]["allow_redirects"] is False


def test_hyperliquid_agent_wallet_error_safety_source_guard() -> None:
    with open(hyperliquid_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    agent_block = source[source.index("# Agent Wallet Endpoints"):]

    forbidden = (
        "Failed to query extraAgents for {wallet_address}: {e}",
        'detail=f"approve_agent failed: {result}"',
        'detail=f"approve_agent error: {approve_result}"',
        'detail=f"Agent upgrade failed: {str(e)}"',
        'detail=f"Invalid agent private key: {e}"',
        'detail=f"Agent wallet configuration failed: {str(e)}"',
        'detail=f"Failed to get agent status: {str(e)}"',
        'detail=f"Failed to check wallet upgrade: {str(e)}"',
        "Failed to configure agent wallet: {e}",
        "Failed to get agent wallet status: {e}",
        "Failed to check wallet upgrade: {e}",
        "Failed to check builder fee for agent wallet: {e}",
        "maxBuilderFee={max_fee}",
        "approve_agent failed: {result}",
        "approve_agent error: {approve_result}",
        "detail=str(e)",
    )
    for pattern in forbidden:
        assert pattern not in agent_block

    assert "SAFE_HYPERLIQUID_AGENT_WALLET_APPROVAL_FAILED_MESSAGE" in agent_block
    assert "SAFE_HYPERLIQUID_AGENT_WALLET_CONFIG_FAILED_MESSAGE" in agent_block
    assert "SAFE_HYPERLIQUID_AGENT_WALLET_STATUS_FAILED_MESSAGE" in agent_block
    assert "SAFE_HYPERLIQUID_AGENT_WALLET_UPGRADE_CHECK_FAILED_MESSAGE" in agent_block
    assert "allow_redirects=False" in agent_block
