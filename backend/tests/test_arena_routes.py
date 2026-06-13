from types import SimpleNamespace

from sqlalchemy.exc import ProgrammingError

from api import arena_routes


class DbStub:
    pass


class SnapshotQueryStub:
    def order_by(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        raise ProgrammingError(
            "SELECT * FROM hyperliquid_trades",
            {},
            Exception("private_key=secret token=secret"),
        )


class SnapshotDbStub:
    closed = False

    def query(self, *args, **kwargs):
        return SnapshotQueryStub()

    def close(self):
        self.closed = True


def test_arena_trades_snapshot_failure_returns_empty_feed(monkeypatch):
    snapshot_db = SnapshotDbStub()

    monkeypatch.setattr(arena_routes, "_current_user_account_ids", lambda *args, **kwargs: [1])
    monkeypatch.setattr(arena_routes, "SnapshotSessionLocal", lambda: snapshot_db)

    response = arena_routes.get_completed_trades(
        limit=20,
        account_id=None,
        trading_mode="testnet",
        wallet_address=None,
        symbol=None,
        exchange=None,
        db=DbStub(),
        current_user=SimpleNamespace(id=7),
    )

    assert snapshot_db.closed is True
    assert response["accounts"] == []
    assert response["trades"] == []
    assert "generated_at" in response
