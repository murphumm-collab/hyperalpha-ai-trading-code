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


def _build_client(tmp_path):
    db_path = tmp_path / "ai_trading_routes.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    user = User(username="ai-trading-test-user", is_active="true")
    session.add(user)
    session.commit()
    session.refresh(user)
    user_id = user.id
    session.close()

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_dependency] = lambda: SimpleNamespace(id=user_id)
    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


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
    assert calls[0]["headers"]["Authorization"] == "Bearer test-token"

    final_runtime = client.get("/api/ai-trading/runtime").json()
    assert final_runtime["strategy_specs"]["by_status"]["approved"] == 1
    assert final_runtime["signal_events"]["by_status"]["submitted"] == 1
    assert final_runtime["signal_events"]["handoff_eligibility"]["review_candidates"] == 0
    assert final_runtime["signal_events"]["handoff_eligibility"]["eligible"] == 0
