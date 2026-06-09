from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.ai_trading_strategy_spec_service as strategy_service
from api.ai_trading_routes import router
from api.auth_utils import get_current_user_dependency
from database.connection import Base, get_db
from database.models import User


def _build_clients(tmp_path, usernames=("ai-trading-test-user",)):
    db_path = tmp_path / "ai_trading_routes.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    user_ids = {}
    for username in usernames:
        user = User(username=username, is_active="true")
        session.add(user)
        session.flush()
        user_ids[username] = user.id
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
        clients[username] = TestClient(app)
    return clients


def _build_client(tmp_path):
    return _build_clients(tmp_path)["ai-trading-test-user"]


def _create_approved_signal_event(client, *, symbol="BTC"):
    draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": symbol,
            "strategy_text": (
                "15m long breakout with stop-loss below invalidation "
                "and take-profit at range high"
            ),
            "max_loss_pct": 1,
            "max_leverage": 3,
        },
    )
    assert draft.status_code == 200

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": draft.json()["spec"], "name": f"{symbol} review spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]

    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest"}},
    )
    assert event_response.status_code == 200
    return approved.json()["spec_record"], event_response.json()["signal_event"]


def test_ai_trading_strategy_signal_and_handoff_flow(tmp_path, monkeypatch):
    client = _build_client(tmp_path)

    runtime = client.get("/api/ai-trading/runtime")
    assert runtime.status_code == 200
    assert runtime.json()["gateway"]["url_configured"] is False

    draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": (
                "15m long breakout with stop-loss below invalidation "
                "and take-profit at range high"
            ),
            "max_loss_pct": 1,
            "max_leverage": 3,
        },
    )
    assert draft.status_code == 200
    spec = draft.json()["spec"]
    assert spec["validation"]["safe_to_emit_signal"] is True
    assert spec["execution"]["ai_may_place_orders"] is False

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": spec, "name": "BTC review spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]
    assert record["status"] == "ready_for_review"

    pre_approval_event = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {}},
    )
    assert pre_approval_event.status_code == 400

    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["spec_record"]["status"] == "approved"

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest"}},
    )
    assert event_response.status_code == 200
    event = event_response.json()["signal_event"]
    assert event["status"] == "review_candidate"
    assert event["signal"]["execution_boundary"]["not_an_order"] is True
    assert event["signal"]["execution_boundary"]["ai_may_place_orders"] is False
    assert event["signal"]["signal_event_id"] == event["id"]
    assert event["signal"]["idempotency_key"] == f"signal_event:{event['id']}"
    assert event["handoff_eligibility"]["eligible"] is False
    assert "gateway_disabled" in event["handoff_eligibility"]["blockers"]

    listed_events = client.get("/api/ai-trading/signal-events")
    assert listed_events.status_code == 200
    assert listed_events.json()["signal_events"][0]["id"] == event["id"]
    assert listed_events.json()["signal_events"][0]["handoff_eligibility"]["eligible"] is False

    disabled_handoff = client.post(f"/api/ai-trading/signal-events/{event['id']}/handoff")
    assert disabled_handoff.status_code == 409
    disabled_attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert disabled_attempts.status_code == 200
    disabled_attempt = disabled_attempts.json()["attempts"][0]
    assert disabled_attempt["result"] == "blocked"
    assert disabled_attempt["gateway_ready"] is False
    assert "gateway_disabled" in disabled_attempt["blockers"]

    disabled_runtime = client.get("/api/ai-trading/runtime").json()
    disabled_handoff_summary = disabled_runtime["signal_events"]["handoff_eligibility"]
    assert disabled_handoff_summary["review_candidates"] == 1
    assert disabled_handoff_summary["eligible"] == 0
    assert disabled_handoff_summary["blocked"] == 1
    assert disabled_handoff_summary["by_blocker"]["gateway_disabled"] == 1

    reject_event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 101000, "source": "pytest-reject"}},
    )
    assert reject_event_response.status_code == 200
    reject_event = reject_event_response.json()["signal_event"]
    assert reject_event["signal"]["idempotency_key"] == f"signal_event:{reject_event['id']}"
    assert reject_event["signal"]["idempotency_key"] != event["signal"]["idempotency_key"]
    rejected = client.post(
        f"/api/ai-trading/signal-events/{reject_event['id']}/reject",
        json={"reason": "pytest rejected before handoff"},
    )
    assert rejected.status_code == 200
    rejected_event = rejected.json()["signal_event"]
    assert rejected_event["status"] == "rejected"
    assert rejected_event["handoff_status"] == "rejected"
    assert rejected_event["signal"]["validation"]["eligible_for_backend_handoff"] is False
    assert rejected_event["signal"]["review"]["reason"] == "pytest rejected before handoff"
    rejected_handoff = client.post(f"/api/ai-trading/signal-events/{reject_event['id']}/handoff")
    assert rejected_handoff.status_code == 400

    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    assert enabled_detail.json()["signal_event"]["handoff_eligibility"]["eligible"] is True
    enabled_runtime = client.get("/api/ai-trading/runtime").json()
    enabled_handoff_summary = enabled_runtime["signal_events"]["handoff_eligibility"]
    assert enabled_handoff_summary["review_candidates"] == 1
    assert enabled_handoff_summary["eligible"] == 1
    assert enabled_handoff_summary["blocked"] == 0

    submitted = client.post(f"/api/ai-trading/signal-events/{event['id']}/handoff")
    assert submitted.status_code == 200
    submitted_event = submitted.json()["signal_event"]
    assert submitted_event["status"] == "submitted"
    assert submitted_event["handoff_status"] == "submitted"
    assert submitted_event["signal"]["execution_boundary"]["handoff_status"] == "submitted"
    assert submitted_event["handoff_eligibility"]["eligible"] is False
    assert "event_status_not_review_candidate" in submitted_event["handoff_eligibility"]["blockers"]
    assert "handoff_already_submitted" in submitted_event["handoff_eligibility"]["blockers"]

    submitted_attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert submitted_attempts.status_code == 200
    attempt_rows = submitted_attempts.json()["attempts"]
    assert [row["result"] for row in attempt_rows] == ["submitted", "blocked"]
    assert attempt_rows[0]["gateway_ready"] is True
    assert attempt_rows[0]["eligibility"]["eligible"] is True
    assert "test-token" not in str(attempt_rows)
    assert "order-backend.test" not in str(attempt_rows)

    assert calls
    assert calls[0]["json"]["type"] == "AI_TRADING_SIGNAL_CANDIDATE"
    assert calls[0]["json"]["idempotency_key"] == submitted_event["signal"]["idempotency_key"]
    assert calls[0]["headers"]["Authorization"] == "Bearer test-token"

    final_runtime = client.get("/api/ai-trading/runtime").json()
    assert final_runtime["strategy_specs"]["by_status"]["approved"] == 1
    assert final_runtime["signal_events"]["by_status"]["submitted"] == 1
    assert final_runtime["signal_events"]["by_status"]["rejected"] == 1
    assert final_runtime["signal_events"]["handoff_eligibility"]["review_candidates"] == 0
    assert final_runtime["signal_events"]["handoff_eligibility"]["eligible"] == 0


def test_ai_trading_routes_isolate_strategy_specs_and_signal_events_by_user(tmp_path):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]

    alice_spec, alice_event = _create_approved_signal_event(alice, symbol="ETH")

    disabled_handoff = alice.post(f"/api/ai-trading/signal-events/{alice_event['id']}/handoff")
    assert disabled_handoff.status_code == 409
    alice_attempts = alice.get(
        f"/api/ai-trading/signal-events/{alice_event['id']}/handoff-attempts"
    )
    assert alice_attempts.status_code == 200
    assert alice_attempts.json()["attempts"][0]["result"] == "blocked"

    assert bob.get("/api/ai-trading/strategy-specs").json()["specs"] == []
    assert bob.get("/api/ai-trading/signal-events").json()["signal_events"] == []

    assert bob.get(f"/api/ai-trading/strategy-specs/{alice_spec['id']}").status_code == 404
    assert bob.post(f"/api/ai-trading/strategy-specs/{alice_spec['id']}/approve").status_code == 404
    assert bob.delete(f"/api/ai-trading/strategy-specs/{alice_spec['id']}").status_code == 404
    assert (
        bob.post(
            f"/api/ai-trading/strategy-specs/{alice_spec['id']}/signal-preview",
            json={"market_context": {}},
        ).status_code
        == 404
    )
    assert (
        bob.post(
            f"/api/ai-trading/strategy-specs/{alice_spec['id']}/signal-events",
            json={"market_context": {}},
        ).status_code
        == 404
    )

    assert bob.get(f"/api/ai-trading/signal-events/{alice_event['id']}").status_code == 404
    assert (
        bob.post(
            f"/api/ai-trading/signal-events/{alice_event['id']}/reject",
            json={"reason": "bob cannot reject alice event"},
        ).status_code
        == 404
    )
    assert bob.post(f"/api/ai-trading/signal-events/{alice_event['id']}/handoff").status_code == 404
    assert (
        bob.get(
            f"/api/ai-trading/signal-events/{alice_event['id']}/handoff-attempts"
        ).status_code
        == 404
    )

    assert alice.get("/api/ai-trading/strategy-specs").json()["specs"][0]["id"] == alice_spec["id"]
    assert alice.get("/api/ai-trading/signal-events").json()["signal_events"][0]["id"] == alice_event["id"]
