from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth_utils import get_current_user_dependency
from api.kline_routes import get_db, router
from database.connection import Base
from database.models import CryptoKline, User, UserExchangeConfig


def _build_clients(tmp_path, usernames=("alice", "bob")):
    db_path = tmp_path / "kline_routes.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    user_ids = {}
    for username in usernames:
        user = User(username=f"kline-{username}", is_active="true")
        session.add(user)
        session.flush()
        user_ids[username] = int(user.id)
        session.add(UserExchangeConfig(
            user_id=user.id,
            selected_exchange="binance" if username == "bob" else "hyperliquid",
        ))
    session.commit()
    session.close()

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    clients = {}
    for username, user_id in user_ids.items():
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user_dependency] = (
            lambda resolved_user_id=user_id: SimpleNamespace(id=resolved_user_id)
        )
        app.dependency_overrides[get_db] = override_db
        client = TestClient(app)
        client._kline_session_factory = Session
        client._kline_user_ids = user_ids
        clients[username] = client
    return clients


def _insert_kline(
    client,
    *,
    exchange="hyperliquid",
    symbol="BTC",
    period="1h",
    timestamp=1_780_000_000,
    close=100.0,
    environment="mainnet",
):
    session = client._kline_session_factory()
    try:
        session.add(CryptoKline(
            exchange=exchange,
            symbol=symbol,
            market="CRYPTO",
            period=period,
            timestamp=timestamp,
            datetime_str=f"2026-06-12T{timestamp % 24:02d}:00:00Z",
            environment=environment,
            open_price=Decimal(str(close - 1)),
            high_price=Decimal(str(close + 2)),
            low_price=Decimal(str(close - 2)),
            close_price=Decimal(str(close)),
            volume=Decimal("1234.5"),
            amount=Decimal("4567.8"),
            change=Decimal("1.25"),
            percent=Decimal("0.75"),
        ))
        session.commit()
    finally:
        session.close()


def test_kline_data_reads_local_db_with_user_exchange_preference(tmp_path):
    clients = _build_clients(tmp_path)
    alice = clients["alice"]
    bob = clients["bob"]
    _insert_kline(alice, exchange="hyperliquid", symbol="BTC", timestamp=100, close=101)
    _insert_kline(alice, exchange="binance", symbol="BTC", timestamp=100, close=202)

    alice_response = alice.get("/api/klines/data?symbol=btc&period=1h")
    bob_response = bob.get("/api/klines/data?symbol=BTC&period=1h")

    assert alice_response.status_code == 200
    assert bob_response.status_code == 200
    alice_payload = alice_response.json()
    bob_payload = bob_response.json()
    assert alice_payload["success"] is True
    assert alice_payload["source"] == "local_db"
    assert alice_payload["exchange"] == "hyperliquid"
    assert alice_payload["matched_symbol"] == "BTC"
    assert alice_payload["data"][0]["close"] == 101.0
    assert bob_payload["exchange"] == "binance"
    assert bob_payload["data"][0]["close"] == 202.0
    assert "not implemented" not in str(alice_payload).lower()


def test_kline_data_applies_limit_and_time_window(tmp_path):
    client = _build_clients(tmp_path)["alice"]
    for idx in range(5):
        _insert_kline(client, timestamp=100 + idx, close=100 + idx)

    response = client.get("/api/klines/data?symbol=BTC&period=1h&start_ts=101&end_ts=104&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert [item["timestamp"] for item in payload["data"]] == [103, 104]
    assert [item["close"] for item in payload["data"]] == [103.0, 104.0]


def test_kline_data_rejects_malformed_inputs_without_raw_exception(tmp_path):
    client = _build_clients(tmp_path)["alice"]

    bad_symbol = client.get("/api/klines/data?symbol=api_key=secret&period=1h")
    bad_period = client.get("/api/klines/data?symbol=BTC&period=7m")
    bad_window = client.get("/api/klines/data?symbol=BTC&period=1h&start_ts=200&end_ts=100")

    assert bad_symbol.status_code == 400
    assert bad_symbol.json()["detail"] == "Invalid symbol"
    assert "secret" not in str(bad_symbol.json()).lower()
    assert bad_period.status_code == 400
    assert bad_period.json()["detail"] == "Unsupported period"
    assert bad_window.status_code == 400
    assert bad_window.json()["detail"] == "start_ts must be <= end_ts"
