from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.ai_trading_market_universe_service as market_universe_service
import services.ai_trading_strategy_spec_service as strategy_service
from api.ai_trading_routes import router
from api.auth_utils import get_current_user_dependency
from database.connection import Base, get_db
from database.models import Account, AccountProgramBinding, BacktestResult, TradingProgram, User


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
        client = TestClient(app)
        client._ai_trading_session_factory = Session
        client._ai_trading_user_ids = user_ids
        client._ai_trading_username = username
        clients[username] = client
    return clients


def _build_client(tmp_path):
    return _build_clients(tmp_path)["ai-trading-test-user"]


def _attach_passing_backtest(client, spec_id):
    response = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/backtest-summary",
        json={
            "backtest_id": f"bt_pytest_{spec_id}",
            "status": "passed",
            "accepted_for_handoff": True,
            "metrics": {
                "total_return": 0.12,
                "max_drawdown": -0.03,
                "sharpe": 1.6,
                "trade_count": 42,
            },
            "period": {
                "start": "2026-01-01",
                "end": "2026-06-01",
            },
            "source": "pytest",
        },
    )
    assert response.status_code == 200
    return response.json()["spec_record"]


def _create_program_backtest_result(
    client,
    *,
    username=None,
    status="completed",
    total_trades=12,
    total_pnl_percent=8.5,
    max_drawdown_percent=-2.25,
):
    session_factory = client._ai_trading_session_factory
    user_ids = client._ai_trading_user_ids
    owner_username = username or client._ai_trading_username
    user_id = user_ids[owner_username]
    session = session_factory()
    try:
        account = Account(
            user_id=user_id,
            name=f"{owner_username} program backtest account",
            account_type="AI",
            is_active="true",
            auto_trading_enabled="false",
            model="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key="not-returned",
            is_deleted=False,
        )
        program = TradingProgram(
            user_id=user_id,
            name=f"{owner_username} AI Trading Program",
            description="pytest owned program",
            code="def run(ctx): return hold('pytest')",
            is_deleted=False,
        )
        session.add_all([account, program])
        session.flush()
        binding = AccountProgramBinding(
            account_id=account.id,
            program_id=program.id,
            signal_pool_ids="[]",
            trigger_interval=300,
            scheduled_trigger_enabled=True,
            is_active=True,
            is_deleted=False,
            exchange="hyperliquid",
        )
        session.add(binding)
        session.flush()

        now = datetime.now(timezone.utc)
        backtest = BacktestResult(
            backtest_type="program",
            binding_id=binding.id,
            user_id=user_id,
            config='{"symbols":["BTC"],"scheduled_interval_sec":300}',
            start_time=now - timedelta(days=30),
            end_time=now,
            initial_balance=10000,
            final_equity=10850,
            total_pnl=850,
            total_pnl_percent=total_pnl_percent,
            max_drawdown=225,
            max_drawdown_percent=max_drawdown_percent,
            total_triggers=32,
            total_trades=total_trades,
            winning_trades=8,
            losing_trades=4,
            win_rate=66.67,
            profit_factor=1.8,
            sharpe_ratio=1.4,
            equity_curve="[]",
            execution_time_ms=1234,
            status=status,
            exchange="hyperliquid",
            completed_at=now if status == "completed" else None,
        )
        session.add(backtest)
        session.commit()
        return backtest.id
    finally:
        session.close()


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
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
            "model_source": "pytest",
        },
    )
    assert draft.status_code == 200

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": draft.json()["spec"], "name": f"{symbol} review spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]
    record = _attach_passing_backtest(client, record["id"])

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
    assert spec["ai_model"]["provider"] is None
    assert "ai_model_provider_missing" in spec["validation"]["warnings"]

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": spec, "name": "BTC review spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]
    assert record["status"] == "ready_for_review"
    assert record["spec"]["backtest"]["status"] == "not_run"
    assert "strategy_backtest_required_before_handoff" in record["validation"]["warnings"]

    pre_approval_event = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {}},
    )
    assert pre_approval_event.status_code == 400

    record = _attach_passing_backtest(client, record["id"])
    assert record["spec"]["backtest"]["accepted_for_handoff"] is True
    assert record["spec"]["backtest"]["backtest_id"] == f"bt_pytest_{record['id']}"

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
    assert event["signal"]["backtest"]["accepted_for_handoff"] is True
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


def test_ai_trading_signal_handoff_requires_accepted_backtest_summary(tmp_path, monkeypatch):
    client = _build_client(tmp_path)

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
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
        },
    )
    assert draft.status_code == 200
    spec = draft.json()["spec"]

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": spec, "name": "BTC no backtest spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]
    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest-missing-backtest"}},
    )
    assert event_response.status_code == 200
    event = event_response.json()["signal_event"]
    assert event["signal"]["backtest"]["accepted_for_handoff"] is False
    assert event["signal"]["validation"]["eligible_for_backend_handoff"] is False
    assert "strategy_backtest_required_before_handoff" in event["handoff_eligibility"]["blockers"]

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called without an accepted backtest")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    blockers = enabled_detail.json()["signal_event"]["handoff_eligibility"]["blockers"]
    assert "strategy_backtest_required_before_handoff" in blockers

    blocked_handoff = client.post(f"/api/ai-trading/signal-events/{event['id']}/handoff")
    assert blocked_handoff.status_code == 400
    assert calls == []
    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["result"] == "blocked"
    assert "strategy_backtest_required_before_handoff" in attempts.json()["attempts"][0]["blockers"]

    _attach_passing_backtest(client, record["id"])
    old_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}").json()["signal_event"]
    assert "strategy_backtest_required_before_handoff" in old_detail["handoff_eligibility"]["blockers"]

    new_event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 101000, "source": "pytest-passed-backtest"}},
    )
    assert new_event_response.status_code == 200
    new_event = new_event_response.json()["signal_event"]
    assert new_event["signal"]["backtest"]["accepted_for_handoff"] is True
    assert new_event["handoff_eligibility"]["eligible"] is True


def test_ai_trading_backtest_summary_requires_quality_metrics(tmp_path, monkeypatch):
    client = _build_client(tmp_path)

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
            "model_provider": "qwen",
            "model_name": "qwen-plus",
        },
    )
    assert draft.status_code == 200

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": draft.json()["spec"], "name": "BTC weak backtest spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]

    weak_backtest = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/backtest-summary",
        json={
            "backtest_id": "bt_weak_metrics",
            "status": "passed",
            "accepted_for_handoff": True,
            "metrics": {"trade_count": 0},
            "source": "pytest",
        },
    )
    assert weak_backtest.status_code == 200
    weak_record = weak_backtest.json()["spec_record"]
    warnings = weak_record["validation"]["warnings"]
    assert "strategy_backtest_required_before_handoff" in warnings
    assert "strategy_backtest_trade_count_required" in warnings
    assert "strategy_backtest_max_drawdown_required" in warnings
    assert "strategy_backtest_performance_metric_required" in warnings

    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest-weak-backtest"}},
    )
    assert event_response.status_code == 200
    event = event_response.json()["signal_event"]
    blockers = event["handoff_eligibility"]["blockers"]
    assert "strategy_backtest_required_before_handoff" in blockers
    assert "strategy_backtest_trade_count_required" in blockers
    assert "strategy_backtest_max_drawdown_required" in blockers
    assert "strategy_backtest_performance_metric_required" in blockers
    assert event["signal"]["validation"]["eligible_for_backend_handoff"] is False

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called with weak backtest metrics")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    assert "strategy_backtest_trade_count_required" in (
        enabled_detail.json()["signal_event"]["handoff_eligibility"]["blockers"]
    )

    blocked_handoff = client.post(f"/api/ai-trading/signal-events/{event['id']}/handoff")
    assert blocked_handoff.status_code == 400
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["result"] == "blocked"
    assert "strategy_backtest_trade_count_required" in attempts.json()["attempts"][0]["blockers"]

    _attach_passing_backtest(client, record["id"])
    new_event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 101000, "source": "pytest-strong-backtest"}},
    )
    assert new_event_response.status_code == 200
    new_event = new_event_response.json()["signal_event"]
    assert new_event["handoff_eligibility"]["eligible"] is True
    assert new_event["signal"]["validation"]["eligible_for_backend_handoff"] is True


def test_ai_trading_can_attach_owned_program_backtest_result(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    backtest_result_id = _create_program_backtest_result(client)

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
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
        },
    )
    assert draft.status_code == 200

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": draft.json()["spec"], "name": "BTC program backtest spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]

    linked = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/backtest-result",
        json={"backtest_result_id": backtest_result_id, "accepted_for_handoff": True},
    )
    assert linked.status_code == 200
    linked_record = linked.json()["spec_record"]
    backtest = linked_record["spec"]["backtest"]
    assert backtest["source"] == "program_backtest_result"
    assert backtest["backtest_id"] == f"program_backtest:{backtest_result_id}"
    assert backtest["accepted_for_handoff"] is True
    assert backtest["program_backtest_result_id"] == backtest_result_id
    assert backtest["metrics"]["trade_count"] == 12
    assert backtest["metrics"]["max_drawdown"] == -2.25
    assert "strategy_backtest_required_before_handoff" not in linked_record["validation"]["warnings"]

    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest-program-backtest"}},
    )
    assert event_response.status_code == 200
    event = event_response.json()["signal_event"]
    assert event["signal"]["backtest"]["source"] == "program_backtest_result"
    assert event["signal"]["validation"]["eligible_for_backend_handoff"] is True

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    assert enabled_detail.json()["signal_event"]["handoff_eligibility"]["eligible"] is True


def test_ai_trading_program_backtest_result_attachment_is_user_scoped(tmp_path):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]
    alice_backtest_id = _create_program_backtest_result(alice, username="alice")

    bob_draft = bob.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": (
                "15m long breakout with stop-loss below invalidation "
                "and take-profit at range high"
            ),
            "max_loss_pct": 1,
            "max_leverage": 3,
            "model_provider": "qwen",
            "model_name": "qwen-plus",
        },
    )
    assert bob_draft.status_code == 200
    bob_saved = bob.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": bob_draft.json()["spec"], "name": "Bob spec", "source": "pytest"},
    )
    assert bob_saved.status_code == 200
    bob_spec_id = bob_saved.json()["spec_record"]["id"]

    cross_attach = bob.post(
        f"/api/ai-trading/strategy-specs/{bob_spec_id}/backtest-result",
        json={"backtest_result_id": alice_backtest_id, "accepted_for_handoff": True},
    )
    assert cross_attach.status_code == 404

    bob_backtest_id = _create_program_backtest_result(bob, username="bob")
    own_attach = bob.post(
        f"/api/ai-trading/strategy-specs/{bob_spec_id}/backtest-result",
        json={"backtest_result_id": bob_backtest_id, "accepted_for_handoff": True},
    )
    assert own_attach.status_code == 200
    assert own_attach.json()["spec_record"]["spec"]["backtest"]["program_backtest_result_id"] == bob_backtest_id


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
    assert (
        bob.post(
            f"/api/ai-trading/strategy-specs/{alice_spec['id']}/backtest-summary",
            json={"backtest_id": "bt_bob_cross_user", "status": "passed", "accepted_for_handoff": True},
        ).status_code
        == 404
    )
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


def test_ai_trading_market_universe_returns_crypto_and_hip3_presets(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    market_universe_service.clear_ai_trading_market_universe_cache()

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_post(url, json=None, timeout=None):
        if json and json.get("dex") == "xyz":
            return FakeResponse(
                [
                    {
                        "universe": [
                            {"name": "NVDA", "maxLeverage": 5, "onlyIsolated": True},
                            {"name": "SP500", "maxLeverage": 10},
                        ]
                    },
                    [
                        {"dayNtlVlm": "900", "dayBaseVlm": "3", "markPx": "300", "openInterest": "30"},
                        {"dayNtlVlm": "1200", "dayBaseVlm": "2", "markPx": "6000", "openInterest": "20"},
                    ],
                ]
            )
        return FakeResponse(
            [
                {
                    "universe": [
                        {"name": "BTC", "maxLeverage": 40, "szDecimals": 5},
                        {"name": "ETH", "maxLeverage": 25, "isDelisted": True},
                        {"name": "SOL", "maxLeverage": 20},
                    ]
                },
                [
                    {"dayNtlVlm": "1000", "dayBaseVlm": "10", "markPx": "100", "openInterest": "10"},
                    {"dayNtlVlm": "999999", "dayBaseVlm": "1", "markPx": "1", "openInterest": "1"},
                    {"dayNtlVlm": "500", "dayBaseVlm": "5", "markPx": "50", "openInterest": "5"},
                ],
            ]
        )

    monkeypatch.setattr(market_universe_service.requests, "post", fake_post)

    response = client.get("/api/ai-trading/market-universe?limit=50&hip3_dex=xyz")
    assert response.status_code == 200
    universe = response.json()

    assert universe["venue"] == "hyperliquid"
    assert universe["environment"] == "mainnet"
    assert universe["counts"] == {"crypto": 2, "hip3": 2, "total": 4}
    assert universe["source"]["crypto"] == "hyperliquid_meta_and_asset_contexts"
    assert universe["source"]["hip3"] == "hyperliquid_meta_and_asset_contexts:xyz"
    assert universe["errors"] == {}

    crypto = universe["presets"]["crypto_top_20"]
    assert [market["symbol"] for market in crypto] == ["BTC", "SOL"]
    assert crypto[0]["category"] == "crypto"
    assert crypto[0]["asset_id"] == 0
    assert crypto[0]["volume_24h_usd"] == 1000

    hip3 = universe["presets"]["hip3_top_20"]
    assert [market["coin"] for market in hip3] == ["xyz:SP500", "xyz:NVDA"]
    assert hip3[0]["category"] == "us_index"
    assert hip3[0]["asset_id"] is None
    assert hip3[1]["category"] == "us_stock"
    assert hip3[1]["only_isolated"] is True
    assert hip3[1]["exchange_symbol"] == "xyz:NVDA"


def test_ai_trading_strategy_spec_preserves_hip3_market_identity(tmp_path):
    client = _build_client(tmp_path)

    draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "xyz:NVDA",
            "strategy_text": (
                "15m long breakout on NVDA with stop-loss below invalidation "
                "and take-profit at prior high"
            ),
            "max_loss_pct": 1,
            "max_leverage": 2,
            "model_provider": "qwen",
            "model_name": "qwen-plus",
            "model_source": "pytest",
        },
    )
    assert draft.status_code == 200
    spec = draft.json()["spec"]
    assert spec["symbol"] == "NVDA"
    assert spec["market"]["dex"] == "xyz"
    assert spec["market"]["exchange_symbol"] == "xyz:NVDA"
    assert spec["market"]["display_symbol"] == "NVDA"
    assert spec["market"]["category"] == "us_stock"
    assert spec["ai_model"]["provider"] == "qwen"
    assert spec["ai_model"]["model"] == "qwen-plus"
    assert spec["ai_model"]["source"] == "pytest"
    assert spec["ai_model"]["v1_allowed_provider"] is True

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": spec, "name": "NVDA HIP-3 review spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]

    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 900, "source": "pytest-hip3"}},
    )
    assert event_response.status_code == 200
    signal = event_response.json()["signal_event"]["signal"]
    assert signal["symbol"] == "NVDA"
    assert signal["exchange_symbol"] == "xyz:NVDA"
    assert signal["market"]["dex"] == "xyz"
    assert signal["market"]["category"] == "us_stock"
    assert signal["ai_model"]["provider"] == "qwen"
    assert signal["ai_model"]["model"] == "qwen-plus"


def test_ai_trading_strategy_spec_model_context_and_secret_guard(tmp_path):
    client = _build_client(tmp_path)

    draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": (
                "15m long breakout with stop-loss below invalidation "
                "and take-profit at prior high"
            ),
            "max_loss_pct": 1,
            "max_leverage": 3,
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
            "model_source": "hyper_ai_profile",
        },
    )
    assert draft.status_code == 200
    spec = draft.json()["spec"]
    assert spec["ai_model"]["provider"] == "deepseek"
    assert spec["ai_model"]["model"] == "deepseek-chat"
    assert spec["ai_model"]["source"] == "hyper_ai_profile"
    assert spec["ai_model"]["configured"] is True
    assert spec["ai_model"]["v1_allowed_provider"] is True
    assert spec["validation"]["safe_to_emit_signal"] is True

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": spec, "name": "BTC model context spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]

    approved = client.post(f"/api/ai-trading/strategy-specs/{record['id']}/approve")
    assert approved.status_code == 200

    event_response = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest-model"}},
    )
    assert event_response.status_code == 200
    signal = event_response.json()["signal_event"]["signal"]
    assert signal["ai_model"]["provider"] == "deepseek"
    assert signal["ai_model"]["model"] == "deepseek-chat"
    assert "api" not in str(signal["ai_model"]).lower()

    invalid = client.post(
        "/api/ai-trading/strategy-spec/validate",
        json={"spec": {**spec, "ai_model": {**spec["ai_model"], "api_key": "secret-key"}}},
    )
    assert invalid.status_code == 200
    validation = invalid.json()["validation"]
    assert validation["valid"] is False
    assert "ai_model_config_must_not_include_secrets" in validation["issues"]
