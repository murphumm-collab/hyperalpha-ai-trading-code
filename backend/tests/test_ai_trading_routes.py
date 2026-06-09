from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.ai_trading_market_universe_service as market_universe_service
import services.ai_trading_strategy_spec_service as strategy_service
from api.ai_trading_routes import router
from api.auth_utils import get_current_user_dependency
from database.connection import Base, get_db
from database.models import (
    Account,
    AccountProgramBinding,
    AiTradingSignalEventRecord,
    AiTradingSignalHandoffAttemptRecord,
    AiTradingStrategySpecRecord,
    BacktestResult,
    BacktestTriggerLog,
    HyperAiProfile,
    TradingProgram,
    User,
)


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
    symbols=None,
    total_trades=12,
    total_pnl_percent=8.5,
    max_drawdown_percent=-2.25,
    with_trigger_logs=False,
    config_extra=None,
):
    session_factory = client._ai_trading_session_factory
    user_ids = client._ai_trading_user_ids
    owner_username = username or client._ai_trading_username
    user_id = user_ids[owner_username]
    session = session_factory()
    try:
        backtest_symbols = list(symbols or ["BTC"])
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
        backtest_config = {"symbols": backtest_symbols, "scheduled_interval_sec": 300}
        if config_extra:
            backtest_config.update(config_extra)

        backtest = BacktestResult(
            backtest_type="program",
            binding_id=binding.id,
            user_id=user_id,
            config=json.dumps(backtest_config),
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
            equity_curve=json.dumps([
                {"timestamp": int((now - timedelta(days=30)).timestamp() * 1000), "equity": 10000},
                {"timestamp": int((now - timedelta(days=15)).timestamp() * 1000), "equity": 10420},
                {"timestamp": int(now.timestamp() * 1000), "equity": 10850},
            ]),
            execution_time_ms=1234,
            status=status,
            exchange="hyperliquid",
            completed_at=now if status == "completed" else None,
        )
        session.add(backtest)
        session.flush()

        if with_trigger_logs:
            session.add_all([
                BacktestTriggerLog(
                    backtest_id=backtest.id,
                    trigger_index=0,
                    trigger_type="scheduled",
                    trigger_time=now - timedelta(days=2),
                    symbol=backtest_symbols[0],
                    decision_type="program",
                    decision_action="open_long",
                    decision_symbol=backtest_symbols[0],
                    decision_side="long",
                    decision_size=0.1,
                    decision_reason="breakout confirmed",
                    entry_price=100000,
                    fee=3.5,
                    unrealized_pnl=0,
                    realized_pnl=0,
                    equity_before=10000,
                    equity_after=10010,
                    decision_input=json.dumps({"balance": 10000, "api_key": "not-returned"}),
                    decision_output=json.dumps({"operation": "open_long", "reason": "pytest"}),
                ),
                BacktestTriggerLog(
                    backtest_id=backtest.id,
                    trigger_index=1,
                    trigger_type="scheduled",
                    trigger_time=now - timedelta(days=1),
                    symbol=backtest_symbols[0],
                    decision_type="program",
                    decision_action="hold",
                    decision_symbol=backtest_symbols[0],
                    decision_reason="risk unchanged",
                    entry_price=101000,
                    fee=0,
                    unrealized_pnl=42,
                    realized_pnl=0,
                    equity_before=10010,
                    equity_after=10052,
                ),
                BacktestTriggerLog(
                    backtest_id=backtest.id,
                    trigger_index=2,
                    trigger_type="tp",
                    trigger_time=now,
                    symbol=backtest_symbols[0],
                    decision_type="program",
                    decision_action="close",
                    decision_symbol=backtest_symbols[0],
                    decision_side="long",
                    decision_size=0.1,
                    decision_reason="take profit",
                    entry_price=100000,
                    exit_price=108500,
                    fee=3.5,
                    unrealized_pnl=0,
                    realized_pnl=850,
                    equity_before=10052,
                    equity_after=10850,
                ),
            ])
        session.commit()
        return backtest.id
    finally:
        session.close()


def _create_approved_signal_event(
    client,
    *,
    symbol="BTC",
    agent_session_id=None,
    agent_session_name=None,
    agent_context_summary=None,
):
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

    save_payload = {"spec": draft.json()["spec"], "name": f"{symbol} review spec", "source": "pytest"}
    if agent_session_id:
        save_payload["agent_session_id"] = agent_session_id
    if agent_session_name:
        save_payload["agent_session_name"] = agent_session_name
    if agent_context_summary:
        save_payload["agent_context_summary"] = agent_context_summary

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json=save_payload,
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
    assert runtime.json()["gateway"]["target_kind"] == "disabled_or_unconfigured"
    assert runtime.json()["gateway"]["max_handoff_age_seconds"] == int(
        strategy_service.SIGNAL_MAX_HANDOFF_AGE_SECONDS
    )
    assert runtime.json()["model_adjustment"]["ready"] is False
    assert runtime.json()["model_adjustment"]["blockers"] == ["model_profile_not_configured"]
    assert runtime.json()["handoff_attempts"] == {
        "total": 0,
        "by_result": {},
        "gateway_ready": 0,
        "gateway_not_ready": 0,
        "latest": None,
    }

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

    disabled_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert disabled_handoff.status_code == 409
    disabled_attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert disabled_attempts.status_code == 200
    disabled_attempt = disabled_attempts.json()["attempts"][0]
    assert disabled_attempt["result"] == "blocked"
    assert disabled_attempt["gateway_ready"] is False
    assert disabled_attempt["eligibility"]["user_confirmation"] == {"confirmed": True, "source": "pytest"}
    assert "gateway_disabled" in disabled_attempt["blockers"]

    disabled_runtime = client.get("/api/ai-trading/runtime").json()
    disabled_handoff_summary = disabled_runtime["signal_events"]["handoff_eligibility"]
    assert disabled_handoff_summary["review_candidates"] == 1
    assert disabled_handoff_summary["eligible"] == 0
    assert disabled_handoff_summary["blocked"] == 1
    assert disabled_handoff_summary["by_blocker"]["gateway_disabled"] == 1
    assert disabled_runtime["handoff_attempts"]["total"] == 1
    assert disabled_runtime["handoff_attempts"]["by_result"] == {"blocked": 1}
    assert disabled_runtime["handoff_attempts"]["gateway_ready"] == 0
    assert disabled_runtime["handoff_attempts"]["gateway_not_ready"] == 1
    assert disabled_runtime["handoff_attempts"]["latest"]["result"] == "blocked"
    assert disabled_runtime["handoff_attempts"]["latest"]["signal_event_id"] == event["id"]

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
    rejected_handoff = client.post(
        f"/api/ai-trading/signal-events/{reject_event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert rejected_handoff.status_code == 400

    calls = []

    class FakeResponse:
        status_code = 202

        def __init__(self, payload=None):
            self.payload = payload or {}

        def json(self):
            return self.payload

        def raise_for_status(self):
            return None

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse({
            "accepted": True,
            "status": "mock_accepted",
            "idempotency_key": json["idempotency_key"],
            "order_backend_signal_id": "obs_acceptance_1",
            "access_token": "secret-response-token",
            "body": "secret-response-body",
        })

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    assert enabled_detail.json()["signal_event"]["handoff_eligibility"]["eligible"] is True
    enabled_runtime = client.get("/api/ai-trading/runtime").json()
    enabled_handoff_summary = enabled_runtime["signal_events"]["handoff_eligibility"]
    assert enabled_handoff_summary["review_candidates"] == 1
    assert enabled_handoff_summary["eligible"] == 1
    assert enabled_handoff_summary["blocked"] == 0
    assert enabled_runtime["handoff_attempts"]["total"] == 2
    assert enabled_runtime["handoff_attempts"]["by_result"] == {"blocked": 2}
    assert enabled_runtime["handoff_attempts"]["gateway_ready"] == 0

    unconfirmed = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": False, "confirmation_source": "pytest"},
    )
    assert unconfirmed.status_code == 400
    assert "explicit user confirmation" in unconfirmed.json()["detail"]
    assert calls == []
    attempts_after_unconfirmed = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert len(attempts_after_unconfirmed.json()["attempts"]) == 1

    submitted = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
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
    assert attempt_rows[0]["eligibility"]["user_confirmation"] == {"confirmed": True, "source": "pytest"}
    assert attempt_rows[0]["eligibility"]["gateway_response"] == {
        "status_code": 202,
        "response_summary": {
            "accepted": True,
            "status": "mock_accepted",
            "idempotency_key": submitted_event["signal"]["idempotency_key"],
            "order_backend_signal_id": "obs_acceptance_1",
        },
    }
    assert "test-token" not in str(attempt_rows)
    assert "order-backend.test" not in str(attempt_rows)
    assert "secret-response-token" not in str(attempt_rows)
    assert "secret-response-body" not in str(attempt_rows)

    assert calls
    assert calls[0]["json"]["type"] == "AI_TRADING_SIGNAL_CANDIDATE"
    assert calls[0]["json"]["idempotency_key"] == submitted_event["signal"]["idempotency_key"]
    assert calls[0]["json"]["user_confirmation"] == {"confirmed": True, "source": "pytest"}
    assert calls[0]["headers"]["Authorization"] == "Bearer test-token"

    final_runtime = client.get("/api/ai-trading/runtime").json()
    assert final_runtime["strategy_specs"]["by_status"]["approved"] == 1
    assert final_runtime["signal_events"]["by_status"]["submitted"] == 1
    assert final_runtime["signal_events"]["by_status"]["rejected"] == 1
    assert final_runtime["signal_events"]["handoff_eligibility"]["review_candidates"] == 0
    assert final_runtime["signal_events"]["handoff_eligibility"]["eligible"] == 0
    assert final_runtime["handoff_attempts"]["total"] == 3
    assert final_runtime["handoff_attempts"]["by_result"] == {"blocked": 2, "submitted": 1}
    assert final_runtime["handoff_attempts"]["gateway_ready"] == 1
    assert final_runtime["handoff_attempts"]["gateway_not_ready"] == 2
    assert final_runtime["handoff_attempts"]["latest"]["result"] == "submitted"
    assert final_runtime["handoff_attempts"]["latest"]["signal_event_id"] == event["id"]
    assert final_runtime["handoff_attempts"]["latest"]["strategy_spec_id"] == record["id"]
    assert "test-token" not in str(final_runtime)
    assert "order-backend.test" not in str(final_runtime)


def test_ai_trading_signal_handoff_requires_production_approval_for_external_gateway(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client, symbol="BTC")

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called without production handoff approval")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", False)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is False
    assert eligibility["gateway_ready"] is False
    assert "production_handoff_approval_required" in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    assert runtime["gateway"]["target_kind"] == "external_order_backend"
    assert runtime["gateway"]["runtime_config_blockers"] == ["production_handoff_approval_required"]
    handoff_summary = runtime["signal_events"]["handoff_eligibility"]
    assert handoff_summary["eligible"] == 0
    assert handoff_summary["blocked"] == 1
    assert handoff_summary["by_blocker"]["production_handoff_approval_required"] == 1

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked_handoff.status_code == 400
    assert "production_handoff_approval_required" in blocked_handoff.json()["detail"]
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    attempt = attempts.json()["attempts"][0]
    assert attempt["result"] == "blocked"
    assert attempt["gateway_ready"] is False
    assert "production_handoff_approval_required" in attempt["blockers"]
    assert "order-backend.test" not in str(attempt)
    assert "test-token" not in str(attempt)


def test_ai_trading_signal_handoff_allows_local_mock_gateway_without_production_approval(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client, symbol="BTC")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "http://127.0.0.1:5621/api/ai-trading/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "local-mock-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", False)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is True
    assert eligibility["gateway_ready"] is True
    assert "production_handoff_approval_required" not in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    assert runtime["gateway"]["target_kind"] == "local_mock"
    assert runtime["gateway"]["runtime_config_blockers"] == []
    assert runtime["gateway"]["default_handoff_status"] == "available"


def test_ai_trading_signal_gateway_payload_contract_is_stable_signal_only(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client, symbol="BTC")

    calls = []

    class FakeResponse:
        status_code = 202

        def raise_for_status(self):
            return None

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest_contract"},
    )

    assert handoff.status_code == 200
    assert len(calls) == 1
    payload = calls[0]["json"]
    assert set(payload.keys()) == {
        "type",
        "version",
        "contract",
        "signal_event_id",
        "strategy_spec_id",
        "user_id",
        "venue",
        "symbol",
        "exchange_symbol",
        "action",
        "idempotency_key",
        "signal_created_at",
        "signal_age_seconds",
        "max_handoff_age_seconds",
        "user_confirmation",
        "market",
        "market_context",
        "risk",
        "backtest",
        "execution_boundary",
        "validation",
        "signal",
    }
    assert payload["type"] == "AI_TRADING_SIGNAL_CANDIDATE"
    assert payload["version"] == "hyperalpha.ai_trading.gateway_message.v1"
    assert payload["contract"] == {
        "name": "AI_TRADING_SIGNAL_CANDIDATE",
        "version": "hyperalpha.ai_trading.gateway_message.v1",
        "signal_version": "hyperalpha.ai_trading.signal_candidate.v1",
        "delivery": "http_json_post",
        "order_authority": "order_backend_only",
    }
    assert payload["signal_event_id"] == event["id"]
    assert payload["strategy_spec_id"] == event["strategy_spec_id"]
    assert payload["user_id"] == event["user_id"]
    assert payload["venue"] == "hyperliquid"
    assert payload["symbol"] == "BTC"
    assert payload["exchange_symbol"] == "BTC"
    assert payload["action"] in {"buy", "sell"}
    assert payload["idempotency_key"] == f"signal_event:{event['id']}"
    assert payload["signal_created_at"]
    assert isinstance(payload["signal_age_seconds"], int)
    assert payload["max_handoff_age_seconds"] == int(strategy_service.SIGNAL_MAX_HANDOFF_AGE_SECONDS)
    assert payload["user_confirmation"] == {"confirmed": True, "source": "pytest_contract"}
    assert payload["market"] == {
        "venue": "hyperliquid",
        "dex": "core",
        "symbol": "BTC",
        "exchange_symbol": "BTC",
        "display_symbol": "BTC",
        "category": "crypto",
    }
    assert payload["market_context"]["mark_price"] == 100000
    assert payload["market_context"]["source"] == "pytest"
    assert payload["risk"]["max_loss_pct"] == 1.0
    assert payload["risk"]["max_leverage"] == 3.0
    assert payload["backtest"]["accepted_for_handoff"] is True
    assert payload["backtest"]["metrics"]["trade_count"] == 42
    assert payload["execution_boundary"]["signal_only"] is True
    assert payload["execution_boundary"]["not_an_order"] is True
    assert payload["execution_boundary"]["requires_user_confirmation"] is True
    assert payload["execution_boundary"]["ai_may_place_orders"] is False
    assert payload["execution_boundary"]["order_backend_only"] is True
    assert payload["validation"]["eligible_for_backend_handoff"] is True
    assert payload["signal"]["idempotency_key"] == payload["idempotency_key"]
    assert payload["signal"]["execution_boundary"] == payload["execution_boundary"]
    assert "order_id" not in payload
    assert "quantity" not in payload
    assert "size" not in payload
    assert "test-token" not in str(payload)
    assert calls[0]["headers"]["Authorization"] == "Bearer test-token"


def test_ai_trading_strategy_spec_natural_language_adjustment_invalidates_approval_and_backtest(tmp_path):
    client = _build_client(tmp_path)
    approved_spec, _ = _create_approved_signal_event(client, symbol="BTC")
    spec_id = approved_spec["id"]

    unpersisted_adjust = client.post(
        "/api/ai-trading/strategy-spec/adjust",
        json={
            "spec": approved_spec["spec"],
            "instruction": (
                "Switch to a 1h short setup, max leverage 2x, max loss 0.5%, "
                "stop loss above breakdown invalidation, take profit at prior support. "
                "Do not place order directly."
            ),
            "source": "pytest_adjust",
        },
    )
    assert unpersisted_adjust.status_code == 200
    adjusted_spec = unpersisted_adjust.json()["spec"]
    assert adjusted_spec["timeframe"] == "1h"
    assert adjusted_spec["entry"]["bias"] == "short"
    assert adjusted_spec["risk"]["max_leverage"] == 2
    assert adjusted_spec["risk"]["max_loss_pct"] == 0.5
    assert adjusted_spec["execution"]["signal_only"] is True
    assert adjusted_spec["execution"]["auto_execution_enabled"] is False
    assert adjusted_spec["execution"]["ai_may_place_orders"] is False
    assert adjusted_spec["execution"]["order_backend_only"] is True
    assert adjusted_spec["metadata"]["last_adjustment"]["direct_order_intent_ignored"] is True
    assert "direct_order_intent_ignored" in adjusted_spec["validation"]["warnings"]

    persisted_adjust = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/adjust",
        json={
            "instruction": (
                "Switch to a 1h short setup, max leverage 2x, max loss 0.5%, "
                "stop loss above breakdown invalidation, take profit at prior support."
            ),
            "source": "pytest_adjust",
        },
    )
    assert persisted_adjust.status_code == 200
    adjusted_record = persisted_adjust.json()["spec_record"]
    adjusted = adjusted_record["spec"]
    assert adjusted_record["status"] == "ready_for_review"
    assert adjusted_record["approved_at"] is None
    assert adjusted["timeframe"] == "1h"
    assert adjusted["entry"]["bias"] == "short"
    assert adjusted["risk"]["max_leverage"] == 2
    assert adjusted["risk"]["max_loss_pct"] == 0.5
    assert adjusted["backtest"]["status"] == "not_run"
    assert adjusted["backtest"]["accepted_for_handoff"] is False
    assert adjusted["backtest"]["source"] == "invalidated_by_strategy_adjustment"
    assert adjusted["backtest"]["previous_backtest_id"] == f"bt_pytest_{spec_id}"
    assert "strategy_backtest_required_before_handoff" in adjusted["validation"]["warnings"]

    preview_after_adjust = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest"}},
    )
    assert preview_after_adjust.status_code == 400
    assert "approved" in preview_after_adjust.json()["detail"]


def test_ai_trading_runtime_reports_model_adjustment_readiness_without_secrets(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    user_id = client._ai_trading_user_ids[client._ai_trading_username]
    session_factory = client._ai_trading_session_factory
    secrets_by_encrypted_value = {
        "encrypted-openai-key": "secret-openai-key",
        "encrypted-qwen-key": "secret-qwen-key",
    }
    monkeypatch.setattr(
        strategy_service,
        "decrypt_private_key",
        lambda encrypted_value: secrets_by_encrypted_value[encrypted_value],
    )
    session = session_factory()
    try:
        session.add(
            HyperAiProfile(
                user_id=user_id,
                llm_provider="openai",
                llm_base_url="https://api.openai.example/v1",
                llm_model="gpt-4o",
                llm_api_key_encrypted="encrypted-openai-key",
            )
        )
        session.commit()
    finally:
        session.close()

    unsupported_runtime = client.get("/api/ai-trading/runtime")
    assert unsupported_runtime.status_code == 200
    unsupported_model = unsupported_runtime.json()["model_adjustment"]
    assert unsupported_model["ready"] is False
    assert unsupported_model["configured"] is True
    assert unsupported_model["provider"] == "openai"
    assert unsupported_model["provider_supported"] is False
    assert "model_provider_not_deepseek_or_qwen" in unsupported_model["blockers"]
    assert unsupported_model["credential_present"] is True
    assert unsupported_model["credential_value_returned"] is False
    unsupported_serialized = str(unsupported_runtime.json())
    assert "secret-openai-key" not in unsupported_serialized
    assert "api.openai.example" not in unsupported_serialized

    session = session_factory()
    try:
        profile = session.query(HyperAiProfile).filter(HyperAiProfile.user_id == user_id).one()
        profile.llm_provider = "qwen"
        profile.llm_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        profile.llm_model = "qwen-plus"
        profile.llm_api_key_encrypted = "encrypted-qwen-key"
        session.commit()
    finally:
        session.close()

    ready_runtime = client.get("/api/ai-trading/runtime")
    assert ready_runtime.status_code == 200
    ready_model = ready_runtime.json()["model_adjustment"]
    assert ready_model == {
        "ready": True,
        "configured": True,
        "provider": "qwen",
        "model": "qwen-plus",
        "source": "hyper_ai_profile",
        "provider_supported": True,
        "blockers": [],
        "credential_present": True,
        "credential_value_returned": False,
    }
    ready_serialized = str(ready_runtime.json())
    assert "secret-qwen-key" not in ready_serialized
    assert "dashscope.aliyuncs.com" not in ready_serialized


def test_ai_trading_strategy_spec_model_adjustment_uses_profile_model_then_safe_adjusts(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    approved_spec, _ = _create_approved_signal_event(
        client,
        symbol="BTC",
        agent_session_id="session:model-btc",
        agent_session_name="BTC Model Session",
        agent_context_summary=(
            "AI Trading session compressed context v1 | symbols=BTC | "
            "risk=0.5%; redaction=enabled; ai_order_placement=disallowed"
        ),
    )
    spec_id = approved_spec["id"]
    calls = []

    def fake_llm_config(db, user_id=None):
        return {
            "configured": True,
            "provider": "qwen",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "api_key": "secret-model-key",
            "api_format": "openai",
        }

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "instruction": (
                                    "Switch to a 1h short setup, max leverage 2x, max loss 0.5%, "
                                    "stop loss above invalidation, take profit at prior support."
                                ),
                                "rationale": "Reduce risk and wait for confirmation.",
                                "risk_notes": ["Re-run backtest before signal handoff."],
                            })
                        }
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "get_llm_config", fake_llm_config)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    response = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/model-adjust",
        json={"instruction": "Use Qwen to reduce risk and make this a short setup", "source": "pytest_model"},
    )

    assert response.status_code == 200
    payload = response.json()
    adjusted_record = payload["spec_record"]
    adjusted = adjusted_record["spec"]
    assert adjusted_record["status"] == "ready_for_review"
    assert adjusted_record["approved_at"] is None
    assert adjusted["timeframe"] == "1h"
    assert adjusted["entry"]["bias"] == "short"
    assert adjusted["risk"]["max_leverage"] == 2
    assert adjusted["risk"]["max_loss_pct"] == 0.5
    assert adjusted["backtest"]["source"] == "invalidated_by_strategy_adjustment"
    assert adjusted["metadata"]["model_adjustment"]["provider"] == "qwen"
    assert adjusted["metadata"]["model_adjustment"]["model"] == "qwen-plus"
    expected_context_summary = (
        "AI Trading session compressed context v1 | symbols=BTC | "
        "risk=0.5%; redaction=enabled; ai_order_placement=disallowed"
    )
    assert adjusted["metadata"]["model_adjustment"]["agent_session_context"] == {
        "agent_session_id": "session:model-btc",
        "agent_session_name": "BTC Model Session",
        "context_summary": expected_context_summary,
        "context_summary_chars": len(expected_context_summary),
        "summary_max_chars": 2000,
        "source": "agent_session",
        "redaction": "enabled",
        "ai_order_placement": "disallowed",
    }
    assert payload["model_context"] == {
        "provider": "qwen",
        "model": "qwen-plus",
        "source": "hyper_ai_profile",
        "agent_session_context": adjusted["metadata"]["model_adjustment"]["agent_session_context"],
    }
    assert payload["model_suggestion"]["risk_notes"] == ["Re-run backtest before signal handoff."]
    assert "secret-model-key" not in str(payload)
    assert calls
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-model-key"
    assert "secret-model-key" not in str(calls[0]["json"])
    model_prompt = json.dumps(calls[0]["json"], ensure_ascii=False)
    assert "Current non-secret AI Trading agent session context" in model_prompt
    assert "session:model-btc" in model_prompt
    assert "AI Trading session compressed context v1" in model_prompt


def test_ai_trading_model_adjustment_redacts_sensitive_agent_session_context(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": "15m breakout with strict stop loss and staged take profit",
            "max_loss_pct": 1,
            "max_leverage": 3,
            "model_provider": "qwen",
            "model_name": "qwen-plus",
            "model_source": "pytest",
        },
    )
    assert draft.status_code == 200
    created_session = client.post(
        "/api/ai-trading/agent-sessions",
        json={
            "agent_session_id": "session:sensitive-btc",
            "name": "Sensitive BTC Session",
            "context_summary": "Safe persisted context.",
        },
    )
    assert created_session.status_code == 200

    calls = []

    def fake_llm_config(db, user_id=None):
        return {
            "configured": True,
            "provider": "qwen",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "api_key": "secret-model-key",
            "api_format": "openai",
        }

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "instruction": "Keep BTC long, reduce max loss to 0.5%, and require a tighter stop loss.",
                                "rationale": "Use a smaller risk budget.",
                                "risk_notes": ["Sensitive context must never reach the model."],
                            })
                        }
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "get_llm_config", fake_llm_config)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    response = client.post(
        "/api/ai-trading/strategy-spec/model-adjust",
        json={
            "spec": draft.json()["spec"],
            "instruction": "Use the current session context and reduce risk",
            "source": "pytest_sensitive_context",
            "agent_session_id": "session:sensitive-btc",
            "agent_session_name": "Sensitive BTC Session",
            "agent_context_summary": "api_key=secret-session-key token=secret-session-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    agent_context = payload["model_context"]["agent_session_context"]
    assert agent_context["agent_session_id"] == "session:sensitive-btc"
    assert agent_context["agent_session_name"] == "Sensitive BTC Session"
    assert agent_context["context_summary"] == "[redacted_sensitive_context]"
    assert agent_context["context_summary_chars"] == len("[redacted_sensitive_context]")
    assert agent_context["summary_max_chars"] == 2000
    assert agent_context["ai_order_placement"] == "disallowed"
    serialized_payload = json.dumps(payload, ensure_ascii=False)
    assert "secret-session-key" not in serialized_payload
    assert "secret-session-token" not in serialized_payload
    assert "secret-model-key" not in serialized_payload

    assert calls
    model_prompt = json.dumps(calls[0]["json"], ensure_ascii=False)
    assert "[redacted_sensitive_context]" in model_prompt
    assert "secret-session-key" not in model_prompt
    assert "secret-session-token" not in model_prompt
    assert "secret-model-key" not in model_prompt


def test_ai_trading_saved_spec_model_adjustment_redacts_sensitive_agent_session_context(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    approved_spec, _ = _create_approved_signal_event(
        client,
        symbol="BTC",
        agent_session_id="session:saved-sensitive-btc",
        agent_session_name="Saved Sensitive BTC Session",
        agent_context_summary="authorization=Bearer secret-saved-session-token private_key=secret-private-key",
    )
    spec_id = approved_spec["id"]
    assert approved_spec["agent_session"]["context_summary"] == "[redacted_sensitive_context]"

    calls = []

    def fake_llm_config(db, user_id=None):
        return {
            "configured": True,
            "provider": "qwen",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "api_key": "secret-model-key",
            "api_format": "openai",
        }

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "instruction": "Keep BTC long, lower max loss to 0.5%, and require a tighter stop loss.",
                                "rationale": "Saved session context must stay redacted.",
                                "risk_notes": ["Re-run backtest before signal handoff."],
                            })
                        }
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "get_llm_config", fake_llm_config)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    response = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/model-adjust",
        json={"instruction": "Use Qwen to reduce saved strategy risk", "source": "pytest_saved_sensitive"},
    )

    assert response.status_code == 200
    payload = response.json()
    agent_context = payload["model_context"]["agent_session_context"]
    assert agent_context["agent_session_id"] == "session:saved-sensitive-btc"
    assert agent_context["agent_session_name"] == "Saved Sensitive BTC Session"
    assert agent_context["context_summary"] == "[redacted_sensitive_context]"
    assert agent_context["context_summary_chars"] == len("[redacted_sensitive_context]")
    assert agent_context["summary_max_chars"] == 2000
    assert agent_context["ai_order_placement"] == "disallowed"
    adjusted = payload["spec_record"]["spec"]
    assert adjusted["metadata"]["model_adjustment"]["agent_session_context"] == agent_context

    serialized_payload = json.dumps(payload, ensure_ascii=False)
    assert "secret-saved-session-token" not in serialized_payload
    assert "secret-private-key" not in serialized_payload
    assert "secret-model-key" not in serialized_payload

    assert calls
    model_prompt = json.dumps(calls[0]["json"], ensure_ascii=False)
    assert "[redacted_sensitive_context]" in model_prompt
    assert "secret-saved-session-token" not in model_prompt
    assert "secret-private-key" not in model_prompt
    assert "secret-model-key" not in model_prompt


def test_ai_trading_unsaved_model_adjustment_requires_current_user_active_agent_session(tmp_path, monkeypatch):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]

    created = alice.post(
        "/api/ai-trading/agent-sessions",
        json={
            "agent_session_id": "session:alice-model-adjust",
            "name": "Alice Model Adjust Session",
            "context_summary": "Alice-only BTC context.",
        },
    )
    assert created.status_code == 200

    bob_draft = bob.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": "15m breakout with strict stop loss and staged take profit",
            "max_loss_pct": 1,
            "max_leverage": 3,
            "model_provider": "qwen",
            "model_name": "qwen-plus",
        },
    )
    assert bob_draft.status_code == 200

    def fail_if_model_config_is_read(db, user_id=None):
        raise AssertionError("model config should not be read before agent-session ownership validation")

    monkeypatch.setattr(strategy_service, "get_llm_config", fail_if_model_config_is_read)

    cross_user = bob.post(
        "/api/ai-trading/strategy-spec/model-adjust",
        json={
            "spec": bob_draft.json()["spec"],
            "instruction": "Use this agent session context",
            "source": "pytest_cross_user_session",
            "agent_session_id": "session:alice-model-adjust",
        },
    )
    assert cross_user.status_code == 404
    assert "not found" in cross_user.json()["detail"].lower()

    archived = alice.delete("/api/ai-trading/agent-sessions/session:alice-model-adjust")
    assert archived.status_code == 200

    alice_draft = alice.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": "15m breakout with strict stop loss and staged take profit",
            "max_loss_pct": 1,
            "max_leverage": 3,
            "model_provider": "qwen",
            "model_name": "qwen-plus",
        },
    )
    assert alice_draft.status_code == 200
    archived_session = alice.post(
        "/api/ai-trading/strategy-spec/model-adjust",
        json={
            "spec": alice_draft.json()["spec"],
            "instruction": "Use the archived agent session context",
            "source": "pytest_archived_session",
            "agent_session_id": "session:alice-model-adjust",
        },
    )
    assert archived_session.status_code == 400
    assert "archived" in archived_session.json()["detail"].lower()


def test_ai_trading_signal_handoff_blocks_stale_signal_events(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)

    session_factory = client._ai_trading_session_factory
    session = session_factory()
    try:
        row = session.query(AiTradingSignalEventRecord).filter(
            AiTradingSignalEventRecord.id == event["id"]
        ).one()
        row.created_at = datetime.now(timezone.utc) - timedelta(
            seconds=int(strategy_service.SIGNAL_MAX_HANDOFF_AGE_SECONDS) + 60
        )
        session.commit()
    finally:
        session.close()

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called for stale signal events")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is False
    assert eligibility["signal_age_seconds"] >= int(strategy_service.SIGNAL_MAX_HANDOFF_AGE_SECONDS)
    assert eligibility["max_handoff_age_seconds"] == int(strategy_service.SIGNAL_MAX_HANDOFF_AGE_SECONDS)
    assert "signal_event_stale_for_handoff" in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    assert runtime["signal_events"]["handoff_eligibility"]["eligible"] == 0
    assert runtime["signal_events"]["handoff_eligibility"]["by_blocker"]["signal_event_stale_for_handoff"] == 1

    handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert handoff.status_code == 400
    assert "signal_event_stale_for_handoff" in handoff.json()["detail"]
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["result"] == "blocked"
    assert attempts.json()["attempts"][0]["eligibility"]["user_confirmation"] == {"confirmed": True, "source": "pytest"}
    assert "signal_event_stale_for_handoff" in attempts.json()["attempts"][0]["blockers"]


def test_ai_trading_signal_handoff_requires_signal_only_boundary(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)

    session = client._ai_trading_session_factory()
    try:
        row = session.query(AiTradingSignalEventRecord).filter(
            AiTradingSignalEventRecord.id == event["id"]
        ).one()
        signal = json.loads(row.signal_json)
        signal["execution_boundary"]["signal_only"] = False
        row.signal_json = json.dumps(signal)
        session.commit()
    finally:
        session.close()

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called when signal_only boundary is missing")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is False
    assert "signal_missing_signal_only_boundary" in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    handoff_summary = runtime["signal_events"]["handoff_eligibility"]
    assert handoff_summary["eligible"] == 0
    assert handoff_summary["by_blocker"]["signal_missing_signal_only_boundary"] == 1

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked_handoff.status_code == 400
    assert "signal_missing_signal_only_boundary" in blocked_handoff.json()["detail"]
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["result"] == "blocked"
    assert "signal_missing_signal_only_boundary" in attempts.json()["attempts"][0]["blockers"]


def test_ai_trading_signal_handoff_requires_user_confirmation_boundary(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)

    session = client._ai_trading_session_factory()
    try:
        row = session.query(AiTradingSignalEventRecord).filter(
            AiTradingSignalEventRecord.id == event["id"]
        ).one()
        signal = json.loads(row.signal_json)
        signal["execution_boundary"]["requires_user_confirmation"] = False
        row.signal_json = json.dumps(signal)
        session.commit()
    finally:
        session.close()

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called without the user-confirmation boundary")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is False
    assert "signal_missing_user_confirmation_boundary" in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    handoff_summary = runtime["signal_events"]["handoff_eligibility"]
    assert handoff_summary["eligible"] == 0
    assert handoff_summary["by_blocker"]["signal_missing_user_confirmation_boundary"] == 1

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked_handoff.status_code == 400
    assert "signal_missing_user_confirmation_boundary" in blocked_handoff.json()["detail"]
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["result"] == "blocked"
    assert "signal_missing_user_confirmation_boundary" in attempts.json()["attempts"][0]["blockers"]


def test_ai_trading_signal_handoff_requires_expected_signal_identity(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)

    session = client._ai_trading_session_factory()
    try:
        row = session.query(AiTradingSignalEventRecord).filter(
            AiTradingSignalEventRecord.id == event["id"]
        ).one()
        signal = json.loads(row.signal_json)
        signal["version"] = "legacy.signal.v0"
        signal["candidate_type"] = "order_instruction"
        signal["venue"] = "binance"
        row.signal_json = json.dumps(signal)
        session.commit()
    finally:
        session.close()

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called for wrong signal identity")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is False
    assert "signal_version_mismatch" in eligibility["blockers"]
    assert "signal_candidate_type_invalid" in eligibility["blockers"]
    assert "signal_venue_must_be_hyperliquid" in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    handoff_summary = runtime["signal_events"]["handoff_eligibility"]
    assert handoff_summary["eligible"] == 0
    assert handoff_summary["by_blocker"]["signal_version_mismatch"] == 1
    assert handoff_summary["by_blocker"]["signal_candidate_type_invalid"] == 1
    assert handoff_summary["by_blocker"]["signal_venue_must_be_hyperliquid"] == 1

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked_handoff.status_code == 400
    assert "signal_version_mismatch" in blocked_handoff.json()["detail"]
    assert "signal_candidate_type_invalid" in blocked_handoff.json()["detail"]
    assert "signal_venue_must_be_hyperliquid" in blocked_handoff.json()["detail"]
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    blockers = attempts.json()["attempts"][0]["blockers"]
    assert "signal_version_mismatch" in blockers
    assert "signal_candidate_type_invalid" in blockers
    assert "signal_venue_must_be_hyperliquid" in blockers


def test_ai_trading_signal_handoff_requires_event_signal_action_symbol_consistency(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client, symbol="BTC")

    session = client._ai_trading_session_factory()
    try:
        row = session.query(AiTradingSignalEventRecord).filter(
            AiTradingSignalEventRecord.id == event["id"]
        ).one()
        signal = json.loads(row.signal_json)
        signal["action"] = "hold"
        signal["symbol"] = "ETH"
        row.signal_json = json.dumps(signal)
        session.commit()
    finally:
        session.close()

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        raise AssertionError("gateway should not be called when signal action/symbol mismatch event")

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    eligibility = detail.json()["signal_event"]["handoff_eligibility"]
    assert eligibility["eligible"] is False
    assert "signal_action_not_tradeable" in eligibility["blockers"]
    assert "signal_event_action_mismatch" in eligibility["blockers"]
    assert "signal_event_symbol_mismatch" in eligibility["blockers"]

    runtime = client.get("/api/ai-trading/runtime").json()
    handoff_summary = runtime["signal_events"]["handoff_eligibility"]
    assert handoff_summary["eligible"] == 0
    assert handoff_summary["by_blocker"]["signal_action_not_tradeable"] == 1
    assert handoff_summary["by_blocker"]["signal_event_action_mismatch"] == 1
    assert handoff_summary["by_blocker"]["signal_event_symbol_mismatch"] == 1

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked_handoff.status_code == 400
    assert "signal_action_not_tradeable" in blocked_handoff.json()["detail"]
    assert "signal_event_action_mismatch" in blocked_handoff.json()["detail"]
    assert "signal_event_symbol_mismatch" in blocked_handoff.json()["detail"]
    assert calls == []

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    blockers = attempts.json()["attempts"][0]["blockers"]
    assert "signal_action_not_tradeable" in blockers
    assert "signal_event_action_mismatch" in blockers
    assert "signal_event_symbol_mismatch" in blockers


def test_ai_trading_failed_gateway_handoff_audit_is_non_secret(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)
    gateway_calls = []

    class FakeGatewayError(Exception):
        def __init__(self, message, response):
            super().__init__(message)
            self.response = response

    class FakeResponse:
        status_code = 502

        def json(self):
            return {
                "accepted": False,
                "status": "rejected",
                "code": "RISK_REJECTED",
                "request_id": "req_gateway_502",
                "authorization": "secret-response-authorization",
                "message": "https://order-backend.test/signals test-token secret-response-body",
            }

        def raise_for_status(self):
            raise FakeGatewayError(
                "https://order-backend.test/signals test-token secret-response-body",
                self,
            )

    def fake_post(url, json=None, headers=None, timeout=None):
        gateway_calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    failed = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert failed.status_code == 400
    assert failed.json()["detail"] == "Signal gateway handoff failed: FakeGatewayError (status 502)"
    assert "order-backend.test" not in str(failed.json())
    assert "test-token" not in str(failed.json())
    assert "secret-response-body" not in str(failed.json())

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    failed_event = detail.json()["signal_event"]
    assert failed_event["handoff_status"] == "failed"
    assert failed_event["error_message"] == "Signal gateway handoff failed: FakeGatewayError (status 502)"
    assert failed_event["handoff_eligibility"]["eligible"] is True
    assert failed_event["handoff_eligibility"]["can_retry"] is True
    assert "order-backend.test" not in str(failed_event)
    assert "test-token" not in str(failed_event)
    assert "secret-response-body" not in str(failed_event)

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    attempt = attempts.json()["attempts"][0]
    assert attempt["result"] == "failed"
    assert attempt["error_message"] == "Signal gateway handoff failed: FakeGatewayError (status 502)"
    assert attempt["eligibility"]["gateway_response"] == {
        "status_code": 502,
        "error_type": "FakeGatewayError",
        "response_summary": {
            "accepted": False,
            "status": "rejected",
            "request_id": "req_gateway_502",
            "code": "RISK_REJECTED",
        },
    }
    assert "order-backend.test" not in str(attempt)
    assert "test-token" not in str(attempt)
    assert "secret-response-body" not in str(attempt)
    assert "secret-response-authorization" not in str(attempt)
    assert len(gateway_calls) == 1

    class SuccessResponse:
        status_code = 202

        def json(self):
            return {
                "accepted": True,
                "status": "mock_accepted_after_retry",
                "idempotency_key": gateway_calls[-1]["json"]["idempotency_key"],
                "order_backend_signal_id": "obs_retry_1",
                "authorization": "secret-success-authorization",
            }

        def raise_for_status(self):
            return None

    def fake_retry_post(url, json=None, headers=None, timeout=None):
        gateway_calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return SuccessResponse()

    monkeypatch.setattr(strategy_service.requests, "post", fake_retry_post)

    retried = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest_retry"},
    )
    assert retried.status_code == 200
    retried_event = retried.json()["signal_event"]
    assert retried_event["status"] == "submitted"
    assert retried_event["handoff_status"] == "submitted"
    assert retried_event["error_message"] is None
    assert retried_event["handoff_eligibility"]["eligible"] is False
    assert "handoff_already_submitted" in retried_event["handoff_eligibility"]["blockers"]

    retry_attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert retry_attempts.status_code == 200
    retry_rows = retry_attempts.json()["attempts"]
    assert [row["result"] for row in retry_rows] == ["submitted", "failed"]
    assert retry_rows[0]["eligibility"]["eligible"] is True
    assert retry_rows[0]["eligibility"]["user_confirmation"] == {
        "confirmed": True,
        "source": "pytest_retry",
    }
    assert retry_rows[0]["eligibility"]["gateway_response"] == {
        "status_code": 202,
        "response_summary": {
            "accepted": True,
            "status": "mock_accepted_after_retry",
            "idempotency_key": retried_event["signal"]["idempotency_key"],
            "order_backend_signal_id": "obs_retry_1",
        },
    }
    assert len(gateway_calls) == 2
    assert gateway_calls[0]["json"]["idempotency_key"] == gateway_calls[1]["json"]["idempotency_key"]
    assert gateway_calls[1]["json"]["user_confirmation"] == {
        "confirmed": True,
        "source": "pytest_retry",
    }
    assert "secret-success-authorization" not in str(retry_rows)


def test_ai_trading_signal_detail_and_gateway_payload_redact_sensitive_fields(tmp_path, monkeypatch):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)

    session_factory = client._ai_trading_session_factory
    session = session_factory()
    try:
        row = session.query(AiTradingSignalEventRecord).filter(
            AiTradingSignalEventRecord.id == event["id"]
        ).one()
        signal = json.loads(row.signal_json)
        signal["api_key"] = "secret-key"
        signal["market_context"]["access_token"] = "secret-token"
        signal["risk"]["nested"] = {"private_key": "secret-private-key"}
        row.signal_json = json.dumps(signal)
        session.commit()
    finally:
        session.close()

    detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert detail.status_code == 200
    serialized_signal = detail.json()["signal_event"]["signal"]
    assert serialized_signal["api_key"] == "***"
    assert serialized_signal["market_context"]["access_token"] == "***"
    assert serialized_signal["risk"]["nested"]["private_key"] == "***"
    assert "secret-key" not in str(serialized_signal)
    assert "secret-token" not in str(serialized_signal)
    assert "secret-private-key" not in str(serialized_signal)

    calls = []

    class FakeResponse:
        status_code = 202

        def raise_for_status(self):
            return None

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_ENABLED", True)
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_URL", "https://order-backend.test/signals")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert handoff.status_code == 200
    assert calls
    gateway_signal = calls[0]["json"]["signal"]
    assert gateway_signal["api_key"] == "***"
    assert gateway_signal["market_context"]["access_token"] == "***"
    assert gateway_signal["risk"]["nested"]["private_key"] == "***"
    assert "secret-key" not in str(calls[0]["json"])
    assert "secret-token" not in str(calls[0]["json"])
    assert "secret-private-key" not in str(calls[0]["json"])


def test_ai_trading_handoff_attempt_responses_redact_sensitive_fields_without_mutating_audit_json(tmp_path):
    client = _build_client(tmp_path)
    _, event = _create_approved_signal_event(client)

    blocked = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked.status_code == 409

    session = client._ai_trading_session_factory()
    try:
        attempt = session.query(AiTradingSignalHandoffAttemptRecord).filter(
            AiTradingSignalHandoffAttemptRecord.signal_event_id == event["id"]
        ).one()
        attempt.blockers_json = json.dumps([
            "gateway_disabled",
            {"access_token": "secret-blocker-token"},
        ])
        attempt.eligibility_json = json.dumps({
            "eligible": False,
            "api_key": "secret-eligibility-key",
            "nested": {
                "private_key": "secret-private-key",
                "gateway_response": {
                    "authorization": "bearer secret-gateway-header",
                },
            },
        })
        session.commit()
        assert "secret-eligibility-key" in attempt.eligibility_json
        assert "secret-blocker-token" in attempt.blockers_json
    finally:
        session.close()

    attempts = client.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    attempt_payload = attempts.json()["attempts"][0]
    assert attempt_payload["blockers"][1]["access_token"] == "***"
    assert attempt_payload["eligibility"]["api_key"] == "***"
    assert attempt_payload["eligibility"]["nested"]["private_key"] == "***"
    assert attempt_payload["eligibility"]["nested"]["gateway_response"]["authorization"] == "***"
    serialized = json.dumps(attempt_payload)
    assert "secret-blocker-token" not in serialized
    assert "secret-eligibility-key" not in serialized
    assert "secret-private-key" not in serialized
    assert "secret-gateway-header" not in serialized


def test_ai_trading_strategy_spec_detail_redacts_sensitive_fields_without_mutating_audit_json(tmp_path):
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
        },
    )
    assert draft.status_code == 200
    spec = draft.json()["spec"]
    spec["api_key"] = "secret-key"
    spec["risk"]["access_token"] = "secret-token"
    spec["execution"]["nested"] = {"private_key": "secret-private-key"}
    spec["metadata"]["password"] = "secret-password"
    spec["watchers"] = [{"authorization": "bearer secret-header"}]

    saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": spec, "name": "BTC polluted spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    saved_record = saved.json()["spec_record"]
    serialized_spec = saved_record["spec"]
    assert serialized_spec["api_key"] == "***"
    assert serialized_spec["risk"]["access_token"] == "***"
    assert serialized_spec["execution"]["nested"]["private_key"] == "***"
    assert serialized_spec["metadata"]["password"] == "***"
    assert serialized_spec["watchers"][0]["authorization"] == "***"
    assert "secret-key" not in str(serialized_spec)
    assert "secret-token" not in str(serialized_spec)
    assert "secret-private-key" not in str(serialized_spec)
    assert "secret-password" not in str(serialized_spec)
    assert "bearer secret-header" not in str(serialized_spec)

    session = client._ai_trading_session_factory()
    try:
        row = session.query(AiTradingStrategySpecRecord).filter(
            AiTradingStrategySpecRecord.id == saved_record["id"]
        ).one()
        assert "secret-key" in row.spec_json
        assert "secret-token" in row.spec_json
        assert "secret-private-key" in row.spec_json
    finally:
        session.close()

    detail = client.get(f"/api/ai-trading/strategy-specs/{saved_record['id']}")
    assert detail.status_code == 200
    detail_spec = detail.json()["spec_record"]["spec"]
    assert detail_spec["api_key"] == "***"
    assert detail_spec["risk"]["access_token"] == "***"
    assert "secret-key" not in str(detail_spec)

    listed = client.get("/api/ai-trading/strategy-specs")
    assert listed.status_code == 200
    assert "spec" not in listed.json()["specs"][0]

    approved = client.post(f"/api/ai-trading/strategy-specs/{saved_record['id']}/approve")
    assert approved.status_code == 200
    approved_spec = approved.json()["spec_record"]["spec"]
    assert approved_spec["api_key"] == "***"
    assert approved_spec["risk"]["access_token"] == "***"
    assert "secret-key" not in str(approved_spec)


def test_ai_trading_runtime_summarizes_strategy_backtest_evidence(tmp_path):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]

    def save_spec(name):
        draft = alice.post(
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
        saved = alice.post(
            "/api/ai-trading/strategy-specs",
            json={"spec": draft.json()["spec"], "name": name, "source": "pytest"},
        )
        assert saved.status_code == 200
        return saved.json()["spec_record"]

    missing = save_spec("BTC missing backtest")
    weak = save_spec("BTC weak backtest")
    passing = save_spec("BTC passing backtest")

    weak_response = alice.post(
        f"/api/ai-trading/strategy-specs/{weak['id']}/backtest-summary",
        json={
            "backtest_id": "bt_weak_runtime",
            "status": "passed",
            "accepted_for_handoff": True,
            "metrics": {},
            "source": "pytest",
        },
    )
    assert weak_response.status_code == 200
    _attach_passing_backtest(alice, passing["id"])

    runtime = alice.get("/api/ai-trading/runtime")
    assert runtime.status_code == 200
    evidence_summary = runtime.json()["strategy_specs"]["backtest_evidence"]
    assert evidence_summary["total"] == 3
    assert evidence_summary["ready"] == 1
    assert evidence_summary["blocked"] == 2
    assert evidence_summary["missing"] == 1
    assert evidence_summary["by_blocker"]["strategy_backtest_required_before_handoff"] == 2
    assert evidence_summary["by_blocker"]["strategy_backtest_trade_count_required"] == 1
    assert evidence_summary["by_blocker"]["strategy_backtest_max_drawdown_required"] == 1
    assert evidence_summary["by_blocker"]["strategy_backtest_performance_metric_required"] == 1

    bob_runtime = bob.get("/api/ai-trading/runtime")
    assert bob_runtime.status_code == 200
    assert bob_runtime.json()["strategy_specs"]["backtest_evidence"]["total"] == 0


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
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    blockers = enabled_detail.json()["signal_event"]["handoff_eligibility"]["blockers"]
    assert "strategy_backtest_required_before_handoff" in blockers

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
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


def test_ai_trading_signal_preview_response_redacts_attached_backtest_sensitive_fields(tmp_path):
    client = _build_client(tmp_path)
    backtest_result_id = _create_program_backtest_result(
        client,
        symbols=["BTC"],
        config_extra={
            "api_key": "secret-preview-key",
            "nested": {
                "access_token": "secret-preview-token",
                "authorization": "bearer secret-preview-header",
            },
        },
    )

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
        json={"spec": draft.json()["spec"], "name": "BTC preview redaction spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    spec_id = saved.json()["spec_record"]["id"]
    linked = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/backtest-result",
        json={"backtest_result_id": backtest_result_id, "accepted_for_handoff": True},
    )
    assert linked.status_code == 200
    approved = client.post(f"/api/ai-trading/strategy-specs/{spec_id}/approve")
    assert approved.status_code == 200

    preview_response = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/signal-preview",
        json={"market_context": {"mark_price": 100000, "source": "pytest-preview"}},
    )
    assert preview_response.status_code == 200
    signal_preview = preview_response.json()["signal_preview"]
    backtest_config = signal_preview["backtest"]["program_backtest_config"]
    assert backtest_config["api_key"] == "***"
    assert backtest_config["nested"]["access_token"] == "***"
    assert backtest_config["nested"]["authorization"] == "***"
    serialized = json.dumps(signal_preview)
    assert "secret-preview-key" not in serialized
    assert "secret-preview-token" not in serialized
    assert "secret-preview-header" not in serialized


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
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)
    monkeypatch.setattr(strategy_service.requests, "post", fake_post)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    assert "strategy_backtest_trade_count_required" in (
        enabled_detail.json()["signal_event"]["handoff_eligibility"]["blockers"]
    )

    blocked_handoff = client.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
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

    listed = client.get("/api/ai-trading/backtest-results?status=completed&symbol=BTC&limit=10")
    assert listed.status_code == 200
    listed_results = listed.json()["backtest_results"]
    assert [row["id"] for row in listed_results] == [backtest_result_id]
    assert listed_results[0]["handoff_ready"] is True
    assert listed_results[0]["symbols"] == ["BTC"]
    assert listed_results[0]["metrics"]["trade_count"] == 12
    assert listed_results[0]["program_name"] == "ai-trading-test-user AI Trading Program"
    assert "not-returned" not in str(listed_results)
    assert "def run" not in str(listed_results)

    assert client.get("/api/ai-trading/backtest-results?status=completed&symbol=ETH").json()[
        "backtest_results"
    ] == []

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
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_TOKEN", "test-token")
    monkeypatch.setattr(strategy_service, "SIGNAL_GATEWAY_PRODUCTION_HANDOFF_APPROVED", True)

    enabled_detail = client.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert enabled_detail.status_code == 200
    assert enabled_detail.json()["signal_event"]["handoff_eligibility"]["eligible"] is True


def test_ai_trading_backtest_evidence_detail_is_non_secret_and_user_scoped(tmp_path):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]
    backtest_result_id = _create_program_backtest_result(
        alice,
        username="alice",
        symbols=["BTC"],
        with_trigger_logs=True,
        config_extra={
            "api_key": "not-returned-config-key",
            "nested": {
                "access_token": "not-returned-config-token",
                "private_key": "not-returned-config-private-key",
            },
        },
    )

    draft = alice.post(
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
    saved = alice.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": draft.json()["spec"], "name": "BTC evidence detail spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    spec_id = saved.json()["spec_record"]["id"]
    linked = alice.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/backtest-result",
        json={"backtest_result_id": backtest_result_id, "accepted_for_handoff": True},
    )
    assert linked.status_code == 200

    evidence_response = alice.get(f"/api/ai-trading/strategy-specs/{spec_id}/backtest-evidence?trigger_limit=2")
    assert evidence_response.status_code == 200
    evidence = evidence_response.json()["evidence"]
    assert evidence["strategy_spec_id"] == spec_id
    assert evidence["strategy_symbol"] == "BTC"
    assert evidence["handoff_ready"] is True
    assert evidence["quality_issues"] == []
    assert evidence["backtest_result"]["id"] == backtest_result_id
    assert evidence["backtest_result"]["symbols"] == ["BTC"]
    assert "api_key" not in evidence["attached_summary"]["program_backtest_config"]
    assert "nested" in evidence["attached_summary"]["program_backtest_config"]
    assert "access_token" not in evidence["attached_summary"]["program_backtest_config"]["nested"]
    assert "private_key" not in evidence["evidence_summary"]["program_backtest_config"]["nested"]
    assert "api_key" not in evidence["backtest_result"]["config"]
    assert len(evidence["backtest_result"]["equity_curve_sample"]) == 3
    assert evidence["trigger_summary"]["total"] == 3
    assert evidence["trigger_summary"]["returned"] == 2
    assert evidence["trigger_summary"]["action_counts"]["open_long"] == 1
    assert evidence["trigger_summary"]["action_counts"]["hold"] == 1
    assert len(evidence["trigger_summary"]["markers"]) == 2
    assert evidence["leakage_guard"]["program_code_returned"] is False
    assert evidence["leakage_guard"]["credential_fields_returned"] is False
    serialized = json.dumps(evidence)
    assert "def run" not in serialized
    assert "not-returned" not in serialized
    assert "api_key" not in serialized
    assert "access_token" not in serialized
    assert "private_key" not in serialized
    assert "decision_input" not in serialized
    assert "decision_output" not in serialized

    bob_cross_user = bob.get(f"/api/ai-trading/strategy-specs/{spec_id}/backtest-evidence")
    assert bob_cross_user.status_code == 404

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
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
        },
    )
    assert bob_draft.status_code == 200
    bob_saved = bob.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": bob_draft.json()["spec"], "name": "Bob no evidence spec", "source": "pytest"},
    )
    assert bob_saved.status_code == 200
    missing = bob.get(
        f"/api/ai-trading/strategy-specs/{bob_saved.json()['spec_record']['id']}/backtest-evidence"
    )
    assert missing.status_code == 400
    assert "No Program Backtest evidence" in missing.json()["detail"]


def test_ai_trading_can_attach_latest_matching_program_backtest_result(tmp_path):
    client = _build_client(tmp_path)
    _create_program_backtest_result(client, symbols=["ETH"])
    weak_btc_backtest_id = _create_program_backtest_result(client, symbols=["BTC"], total_trades=0)
    ready_btc_backtest_id = _create_program_backtest_result(client, symbols=["BTC"])

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
        json={"spec": draft.json()["spec"], "name": "BTC latest backtest spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    record = saved.json()["spec_record"]

    linked = client.post(
        f"/api/ai-trading/strategy-specs/{record['id']}/backtest-result/latest",
        json={"accepted_for_handoff": True},
    )
    assert linked.status_code == 200
    backtest = linked.json()["spec_record"]["spec"]["backtest"]
    assert backtest["program_backtest_result_id"] == ready_btc_backtest_id
    assert backtest["program_backtest_result_id"] != weak_btc_backtest_id
    assert backtest["accepted_for_handoff"] is True
    assert backtest["metrics"]["trade_count"] == 12
    assert "strategy_backtest_required_before_handoff" not in linked.json()["spec_record"]["validation"]["warnings"]

    eth_draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "SOL",
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
    assert eth_draft.status_code == 200
    eth_saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": eth_draft.json()["spec"], "name": "SOL no latest spec", "source": "pytest"},
    )
    assert eth_saved.status_code == 200
    missing = client.post(
        f"/api/ai-trading/strategy-specs/{eth_saved.json()['spec_record']['id']}/backtest-result/latest",
        json={"accepted_for_handoff": True},
    )
    assert missing.status_code == 400
    assert "No handoff-ready Program BacktestResult" in missing.json()["detail"]


def test_ai_trading_backtest_preflight_recommends_owned_symbol_binding(tmp_path):
    client = _build_client(tmp_path)
    _create_program_backtest_result(client, symbols=["BTC"])

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
        json={"spec": draft.json()["spec"], "name": "BTC preflight spec", "source": "pytest"},
    )
    assert saved.status_code == 200
    spec_id = saved.json()["spec_record"]["id"]

    response = client.post(
        f"/api/ai-trading/strategy-specs/{spec_id}/backtest-preflight",
        json={"days": 14, "initial_balance": 25000, "slippage_percent": 0.05, "fee_rate": 0.035},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    preflight = payload["preflight"]
    assert preflight["ready"] is True
    assert preflight["strategy_symbol"] == "BTC"
    assert preflight["program_backtest_endpoint"] == "/api/programs/backtest"
    assert preflight["program_backtest_streaming"] is True
    assert preflight["default_request"]["binding_id"] == preflight["recommended_binding"]["binding_id"]
    assert preflight["default_request"]["initial_balance"] == 25000
    assert preflight["assumptions"]["does_not_execute"] is True
    assert preflight["assumptions"]["requires_user_confirmation"] is True
    assert preflight["recommended_binding"]["eligible"] is True
    assert preflight["recommended_binding"]["symbols"] == ["BTC"]
    assert "not-returned" not in str(preflight)
    assert "def run" not in str(preflight)

    sol_draft = client.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "SOL",
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
    sol_saved = client.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": sol_draft.json()["spec"], "name": "SOL preflight spec", "source": "pytest"},
    )
    sol_response = client.post(
        f"/api/ai-trading/strategy-specs/{sol_saved.json()['spec_record']['id']}/backtest-preflight",
        json={"days": 14},
    )
    assert sol_response.status_code == 200
    sol_preflight = sol_response.json()["preflight"]
    assert sol_preflight["ready"] is False
    assert sol_preflight["default_request"] is None
    assert "no_eligible_symbol_matching_program_binding" in sol_preflight["blockers"]
    assert "binding_symbol_mismatch" in sol_preflight["candidate_bindings"][0]["blockers"]


def test_ai_trading_backtest_preflight_is_user_scoped(tmp_path):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]
    _create_program_backtest_result(alice, username="alice", symbols=["BTC"])

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
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
        },
    )
    bob_saved = bob.post(
        "/api/ai-trading/strategy-specs",
        json={"spec": bob_draft.json()["spec"], "name": "Bob preflight spec", "source": "pytest"},
    )
    response = bob.post(
        f"/api/ai-trading/strategy-specs/{bob_saved.json()['spec_record']['id']}/backtest-preflight",
        json={"days": 30},
    )
    assert response.status_code == 200
    preflight = response.json()["preflight"]
    assert preflight["ready"] is False
    assert preflight["candidate_bindings"] == []
    assert "no_program_bindings" in preflight["blockers"]


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
    bob_listed = bob.get("/api/ai-trading/backtest-results?status=completed&limit=10")
    assert bob_listed.status_code == 200
    bob_rows = bob_listed.json()["backtest_results"]
    assert [row["id"] for row in bob_rows] == [bob_backtest_id]
    assert alice_backtest_id not in [row["id"] for row in bob_rows]

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

    disabled_handoff = alice.post(
        f"/api/ai-trading/signal-events/{alice_event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert disabled_handoff.status_code == 409
    alice_attempts = alice.get(
        f"/api/ai-trading/signal-events/{alice_event['id']}/handoff-attempts"
    )
    assert alice_attempts.status_code == 200
    assert alice_attempts.json()["attempts"][0]["result"] == "blocked"

    assert bob.get("/api/ai-trading/strategy-specs").json()["specs"] == []
    assert bob.get("/api/ai-trading/signal-events").json()["signal_events"] == []
    bob_runtime = bob.get("/api/ai-trading/runtime")
    assert bob_runtime.status_code == 200
    assert bob_runtime.json()["handoff_attempts"] == {
        "total": 0,
        "by_result": {},
        "gateway_ready": 0,
        "gateway_not_ready": 0,
        "latest": None,
    }

    assert bob.get(f"/api/ai-trading/strategy-specs/{alice_spec['id']}").status_code == 404
    assert bob.post(f"/api/ai-trading/strategy-specs/{alice_spec['id']}/approve").status_code == 404
    assert (
        bob.post(
            f"/api/ai-trading/strategy-specs/{alice_spec['id']}/adjust",
            json={"instruction": "Switch Alice strategy to 1h short", "source": "pytest"},
        ).status_code
        == 404
    )
    assert (
        bob.post(
            f"/api/ai-trading/strategy-specs/{alice_spec['id']}/model-adjust",
            json={"instruction": "Ask model to switch Alice strategy", "source": "pytest"},
        ).status_code
        == 404
    )
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


def test_ai_trading_agent_sessions_partition_context_by_user_and_session(tmp_path):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]

    btc_context_summary = "User prefers BTC 15m breakout with strict risk caps."
    btc_spec, btc_event = _create_approved_signal_event(
        alice,
        symbol="BTC",
        agent_session_id="session:btc-breakout",
        agent_session_name="BTC Breakout Agent",
        agent_context_summary=btc_context_summary,
    )
    eth_spec, _ = _create_approved_signal_event(
        alice,
        symbol="ETH",
        agent_session_id="session:eth-mean-reversion",
        agent_session_name="ETH Mean Reversion Agent",
    )

    sessions = alice.get("/api/ai-trading/agent-sessions")
    assert sessions.status_code == 200
    session_rows = sessions.json()["agent_sessions"]
    session_ids = {row["id"] for row in session_rows}
    assert {"session:btc-breakout", "session:eth-mean-reversion"} <= session_ids

    btc_session = next(row for row in session_rows if row["id"] == "session:btc-breakout")
    assert btc_session["name"] == "BTC Breakout Agent"
    assert btc_session["strategy_spec_count"] == 1
    assert btc_session["signal_event_count"] == 1
    assert btc_session["by_strategy_status"]["approved"] == 1
    assert btc_session["by_signal_status"]["review_candidate"] == 1
    assert btc_session["symbols"] == ["BTC"]
    assert "strict risk caps" in btc_session["context_summary"]
    assert btc_session["context_summary_chars"] == len(btc_context_summary)
    assert btc_session["summary_max_chars"] == 2000

    filtered_specs = alice.get("/api/ai-trading/strategy-specs?agent_session_id=session:btc-breakout")
    assert filtered_specs.status_code == 200
    assert [row["id"] for row in filtered_specs.json()["specs"]] == [btc_spec["id"]]
    filtered_spec_session = filtered_specs.json()["specs"][0]["agent_session"]
    assert filtered_spec_session["id"] == "session:btc-breakout"
    assert filtered_spec_session["context_summary_chars"] == len(btc_context_summary)
    assert filtered_spec_session["summary_max_chars"] == 2000

    filtered_events = alice.get("/api/ai-trading/signal-events?agent_session_id=session:btc-breakout")
    assert filtered_events.status_code == 200
    assert [row["id"] for row in filtered_events.json()["signal_events"]] == [btc_event["id"]]
    filtered_event_session = filtered_events.json()["signal_events"][0]["agent_session"]
    assert filtered_event_session["id"] == "session:btc-breakout"
    assert filtered_event_session["context_summary_chars"] == len(btc_context_summary)
    assert filtered_event_session["summary_max_chars"] == 2000

    detail = alice.get(f"/api/ai-trading/signal-events/{btc_event['id']}")
    assert detail.status_code == 200
    assert detail.json()["signal_event"]["signal"]["agent_session"]["id"] == "session:btc-breakout"

    blocked_handoff = alice.post(
        f"/api/ai-trading/signal-events/{btc_event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert blocked_handoff.status_code == 409
    attempts = alice.get(f"/api/ai-trading/signal-events/{btc_event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    attempt_session = attempts.json()["attempts"][0]["agent_session"]
    assert attempt_session["id"] == "session:btc-breakout"
    assert attempt_session["context_summary_chars"] == len(btc_context_summary)
    assert attempt_session["summary_max_chars"] == 2000

    context = alice.get("/api/ai-trading/agent-sessions/session:btc-breakout/context")
    assert context.status_code == 200
    context_payload = context.json()["context"]
    assert context_payload["agent_session"]["id"] == "session:btc-breakout"
    assert context_payload["agent_session"]["context_summary_chars"] == len(btc_context_summary)
    assert context_payload["agent_session"]["summary_max_chars"] == 2000
    assert context_payload["compression"]["secret_policy"] == "redacted_no_credentials"
    assert context_payload["compression"]["attempt_limit"] == 1
    assert context_payload["compression"]["strategy_requested_limit"] == 5
    assert context_payload["compression"]["signal_requested_limit"] == 10
    assert context_payload["compression"]["attempt_requested_limit"] == 20
    assert context_payload["compression"]["strategy_max_limit"] == 20
    assert context_payload["compression"]["signal_max_limit"] == 50
    assert context_payload["compression"]["attempt_max_limit"] == 100
    assert context_payload["compression"]["summary_max_chars"] == 2000
    assert context_payload["strategy_specs"][0]["id"] == btc_spec["id"]
    assert context_payload["signal_events"][0]["id"] == btc_event["id"]
    assert context_payload["handoff_attempts"][0]["signal_event_id"] == btc_event["id"]
    assert context_payload["handoff_attempts"][0]["strategy_spec_id"] == btc_spec["id"]
    assert context_payload["handoff_attempts"][0]["result"] == "blocked"
    assert context_payload["handoff_attempts"][0]["gateway_ready"] is False
    assert "gateway_disabled" in context_payload["handoff_attempts"][0]["blockers"]
    assert context_payload["handoff_attempts"][0]["eligibility"]["user_confirmation"] == {
        "confirmed": True,
        "source": "pytest",
    }
    serialized_context_payload = json.dumps(context_payload).lower()
    assert "api_key" not in serialized_context_payload
    assert "authorization" not in serialized_context_payload
    assert "http://" not in serialized_context_payload
    assert "https://" not in serialized_context_payload
    assert alice.get(
        "/api/ai-trading/agent-sessions/session:btc-breakout/context?strategy_limit=21"
    ).status_code == 422
    assert alice.post(
        "/api/ai-trading/agent-sessions/session:btc-breakout/compress-context?attempt_limit=101"
    ).status_code == 422

    eth_filtered_specs = alice.get("/api/ai-trading/strategy-specs?agent_session_id=session:eth-mean-reversion")
    assert eth_filtered_specs.status_code == 200
    assert [row["id"] for row in eth_filtered_specs.json()["specs"]] == [eth_spec["id"]]
    assert alice.get("/api/ai-trading/signal-events?agent_session_id=session:eth-mean-reversion").json()["signal_events"]

    assert bob.get("/api/ai-trading/agent-sessions").json()["agent_sessions"] == []
    assert bob.get("/api/ai-trading/agent-sessions/session:btc-breakout/context").status_code == 404
    assert bob.get("/api/ai-trading/strategy-specs?agent_session_id=session:btc-breakout").json()["specs"] == []
    assert bob.get("/api/ai-trading/signal-events?agent_session_id=session:btc-breakout").json()["signal_events"] == []


def test_ai_trading_agent_session_crud_updates_metadata_and_archives_by_user(tmp_path, monkeypatch):
    clients = _build_clients(tmp_path, usernames=("alice", "bob"))
    alice = clients["alice"]
    bob = clients["bob"]
    managed_context_summary = "BTC managed session with risk caps."
    renamed_context_summary = "Renamed context summary."

    created = alice.post(
        "/api/ai-trading/agent-sessions",
        json={
            "agent_session_id": "session:managed-btc",
            "name": "Managed BTC Agent",
            "context_summary": managed_context_summary,
        },
    )
    assert created.status_code == 200
    created_session = created.json()["agent_session"]
    assert created_session["id"] == "session:managed-btc"
    assert created_session["status"] == "active"
    assert created_session["context_summary"] == managed_context_summary
    assert created_session["context_summary_chars"] == len(managed_context_summary)
    assert created_session["summary_max_chars"] == 2000

    empty_context = alice.get("/api/ai-trading/agent-sessions/session:managed-btc/context")
    assert empty_context.status_code == 200
    assert empty_context.json()["context"]["agent_session"]["context_summary_chars"] == len(managed_context_summary)
    assert empty_context.json()["context"]["agent_session"]["summary_max_chars"] == 2000
    assert empty_context.json()["context"]["strategy_specs"] == []
    assert empty_context.json()["context"]["signal_events"] == []
    assert empty_context.json()["context"]["handoff_attempts"] == []

    draft = alice.post(
        "/api/ai-trading/strategy-spec/draft",
        json={
            "symbol": "BTC",
            "strategy_text": "15m long breakout with stop-loss and take-profit.",
            "max_loss_pct": 1,
            "max_leverage": 3,
        },
    )
    assert draft.status_code == 200
    saved = alice.post(
        "/api/ai-trading/strategy-specs",
        json={
            "spec": draft.json()["spec"],
            "name": "Managed BTC Spec",
            "source": "pytest",
            "agent_session_id": "session:managed-btc",
        },
    )
    assert saved.status_code == 200
    saved_record = saved.json()["spec_record"]
    assert saved_record["agent_session"]["name"] == "Managed BTC Agent"
    assert saved_record["agent_session"]["status"] == "active"
    assert saved_record["agent_session"]["context_summary_chars"] == len(managed_context_summary)
    assert saved_record["agent_session"]["summary_max_chars"] == 2000

    saved_record = _attach_passing_backtest(alice, saved_record["id"])
    approved = alice.post(f"/api/ai-trading/strategy-specs/{saved_record['id']}/approve")
    assert approved.status_code == 200
    event_response = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest"}},
    )
    assert event_response.status_code == 200
    event = event_response.json()["signal_event"]
    assert event["agent_session"]["status"] == "active"

    disabled_handoff = alice.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest"},
    )
    assert disabled_handoff.status_code == 409

    updated = alice.patch(
        "/api/ai-trading/agent-sessions/session:managed-btc",
        json={
            "name": "Renamed BTC Agent",
            "context_summary": renamed_context_summary,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["agent_session"]["name"] == "Renamed BTC Agent"
    assert updated.json()["agent_session"]["context_summary_chars"] == len(renamed_context_summary)
    assert updated.json()["agent_session"]["summary_max_chars"] == 2000

    detail = alice.get(f"/api/ai-trading/strategy-specs/{saved_record['id']}")
    assert detail.status_code == 200
    assert detail.json()["spec_record"]["agent_session"]["name"] == "Renamed BTC Agent"
    assert detail.json()["spec_record"]["agent_session"]["status"] == "active"
    assert detail.json()["spec_record"]["agent_session"]["context_summary_chars"] == len(renamed_context_summary)
    assert detail.json()["spec_record"]["agent_session"]["summary_max_chars"] == 2000
    signal_detail = alice.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert signal_detail.status_code == 200
    assert signal_detail.json()["signal_event"]["agent_session"]["name"] == "Renamed BTC Agent"
    assert signal_detail.json()["signal_event"]["agent_session"]["status"] == "active"
    attempts = alice.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert attempts.status_code == 200
    assert attempts.json()["attempts"][0]["agent_session"]["name"] == "Renamed BTC Agent"
    assert attempts.json()["attempts"][0]["agent_session"]["status"] == "active"
    attempt_count_before_archive = len(attempts.json()["attempts"])

    compressed = alice.post("/api/ai-trading/agent-sessions/session:managed-btc/compress-context")
    assert compressed.status_code == 200
    compressed_payload = compressed.json()
    context_summary = compressed_payload["context_summary"]
    assert "AI Trading session compressed context v1" in context_summary
    assert "strategy_specs=1" in context_summary
    assert "signal_events=1" in context_summary
    assert "handoff_attempts=1" in context_summary
    assert "blocked:1" in context_summary
    assert "latest_handoff_attempt=#" in context_summary
    assert "redaction=enabled" in context_summary
    assert "ai_order_placement=disallowed" in context_summary
    assert len(context_summary) <= compressed_payload["context"]["compression"]["summary_max_chars"]
    assert compressed_payload["context"]["compression"]["summary_max_chars"] == 2000
    assert compressed_payload["context"]["compression"]["strategy_max_limit"] == 20
    assert compressed_payload["context"]["compression"]["signal_max_limit"] == 50
    assert compressed_payload["context"]["compression"]["attempt_max_limit"] == 100
    assert "api_key" not in json.dumps(compressed_payload).lower()
    assert compressed_payload["agent_session"]["context_summary"] == context_summary
    assert compressed_payload["agent_session"]["context_summary_chars"] == len(context_summary)
    assert compressed_payload["agent_session"]["summary_max_chars"] == 2000
    assert compressed_payload["context"]["agent_session"]["context_summary"] == context_summary
    assert compressed_payload["context"]["agent_session"]["context_summary_chars"] == len(context_summary)
    assert compressed_payload["context"]["agent_session"]["summary_max_chars"] == 2000
    assert compressed_payload["context"]["handoff_attempts"][0]["result"] == "blocked"
    assert compressed_payload["context"]["handoff_attempts"][0]["signal_event_id"] == event["id"]

    detail_after_compress = alice.get(f"/api/ai-trading/strategy-specs/{saved_record['id']}")
    assert detail_after_compress.status_code == 200
    assert detail_after_compress.json()["spec_record"]["agent_session"]["context_summary"] == context_summary
    assert detail_after_compress.json()["spec_record"]["agent_session"]["status"] == "active"
    assert detail_after_compress.json()["spec_record"]["agent_session"]["context_summary_chars"] == len(context_summary)
    assert detail_after_compress.json()["spec_record"]["agent_session"]["summary_max_chars"] == 2000

    assert bob.patch(
        "/api/ai-trading/agent-sessions/session:managed-btc",
        json={"name": "Bob cannot rename Alice session"},
    ).status_code == 404
    assert bob.delete("/api/ai-trading/agent-sessions/session:managed-btc").status_code == 404
    assert bob.post("/api/ai-trading/agent-sessions/session:managed-btc/compress-context").status_code == 404

    archived = alice.delete("/api/ai-trading/agent-sessions/session:managed-btc")
    assert archived.status_code == 200
    assert archived.json()["agent_session"]["status"] == "archived"
    active_sessions = alice.get("/api/ai-trading/agent-sessions")
    assert active_sessions.status_code == 200
    assert all(row["id"] != "session:managed-btc" for row in active_sessions.json()["agent_sessions"])
    archived_sessions = alice.get("/api/ai-trading/agent-sessions?status=archived")
    assert archived_sessions.status_code == 200
    assert archived_sessions.json()["agent_sessions"][0]["id"] == "session:managed-btc"

    detail_after_archive = alice.get(f"/api/ai-trading/strategy-specs/{saved_record['id']}")
    assert detail_after_archive.status_code == 200
    assert detail_after_archive.json()["spec_record"]["agent_session"]["status"] == "archived"

    approve_archived_session_spec = alice.post(f"/api/ai-trading/strategy-specs/{saved_record['id']}/approve")
    assert approve_archived_session_spec.status_code == 400
    assert "archived" in approve_archived_session_spec.json()["detail"]

    backtest_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/backtest-summary",
        json={
            "backtest_id": "bt_after_archive",
            "status": "passed",
            "accepted_for_handoff": True,
            "metrics": {
                "total_return": 0.08,
                "max_drawdown": -0.02,
                "sharpe": 1.2,
                "trade_count": 20,
            },
            "source": "pytest_archived",
        },
    )
    assert backtest_archived_session_spec.status_code == 400
    assert "archived" in backtest_archived_session_spec.json()["detail"]

    backtest_result_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/backtest-result",
        json={"backtest_result_id": 999999, "accepted_for_handoff": True},
    )
    assert backtest_result_archived_session_spec.status_code == 400
    assert "archived" in backtest_result_archived_session_spec.json()["detail"]

    latest_backtest_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/backtest-result/latest",
        json={},
    )
    assert latest_backtest_archived_session_spec.status_code == 400
    assert "archived" in latest_backtest_archived_session_spec.json()["detail"]

    preflight_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/backtest-preflight",
        json={},
    )
    assert preflight_archived_session_spec.status_code == 400
    assert "archived" in preflight_archived_session_spec.json()["detail"]

    adjust_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/adjust",
        json={"instruction": "Continue this archived session as a 1h short setup", "source": "pytest_archived"},
    )
    assert adjust_archived_session_spec.status_code == 400
    assert "archived" in adjust_archived_session_spec.json()["detail"]

    signal_preview_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/signal-preview",
        json={"market_context": {"mark_price": 100000, "source": "pytest_archived"}},
    )
    assert signal_preview_archived_session_spec.status_code == 400
    assert "archived" in signal_preview_archived_session_spec.json()["detail"]

    signal_event_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/signal-events",
        json={"market_context": {"mark_price": 100000, "source": "pytest_archived"}},
    )
    assert signal_event_archived_session_spec.status_code == 400
    assert "archived" in signal_event_archived_session_spec.json()["detail"]

    archived_event_detail = alice.get(f"/api/ai-trading/signal-events/{event['id']}")
    assert archived_event_detail.status_code == 200
    assert archived_event_detail.json()["signal_event"]["agent_session"]["status"] == "archived"
    assert (
        "agent_session_archived"
        in archived_event_detail.json()["signal_event"]["handoff_eligibility"]["blockers"]
    )
    assert archived_event_detail.json()["signal_event"]["handoff_eligibility"]["can_retry"] is False

    archived_handoff = alice.post(
        f"/api/ai-trading/signal-events/{event['id']}/handoff",
        json={"confirmed_by_user": True, "confirmation_source": "pytest_archived"},
    )
    assert archived_handoff.status_code == 400
    assert "archived" in archived_handoff.json()["detail"]
    archived_attempts = alice.get(f"/api/ai-trading/signal-events/{event['id']}/handoff-attempts")
    assert archived_attempts.status_code == 200
    assert len(archived_attempts.json()["attempts"]) == attempt_count_before_archive + 1
    assert archived_attempts.json()["attempts"][0]["agent_session"]["status"] == "archived"
    assert "agent_session_archived" in archived_attempts.json()["attempts"][0]["blockers"]

    def fail_if_model_config_is_read(db, user_id=None):
        raise AssertionError("model config should not be read for an archived agent session")

    monkeypatch.setattr(strategy_service, "get_llm_config", fail_if_model_config_is_read)
    model_adjust_archived_session_spec = alice.post(
        f"/api/ai-trading/strategy-specs/{saved_record['id']}/model-adjust",
        json={"instruction": "Ask Qwen to continue this archived session", "source": "pytest_archived"},
    )
    assert model_adjust_archived_session_spec.status_code == 400
    assert "archived" in model_adjust_archived_session_spec.json()["detail"]

    save_to_archived = alice.post(
        "/api/ai-trading/strategy-specs",
        json={
            "spec": draft.json()["spec"],
            "name": "Should not save",
            "source": "pytest",
            "agent_session_id": "session:managed-btc",
        },
    )
    assert save_to_archived.status_code == 400
    assert "archived" in save_to_archived.json()["detail"]


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
