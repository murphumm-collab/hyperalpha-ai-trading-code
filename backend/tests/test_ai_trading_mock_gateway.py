from fastapi.testclient import TestClient

import dev_ai_trading_signal_gateway as mock_gateway


def _valid_payload():
    return {
        "type": "AI_TRADING_SIGNAL_CANDIDATE",
        "version": "hyperalpha.ai_trading.gateway_message.v1",
        "contract": {
            "name": "AI_TRADING_SIGNAL_CANDIDATE",
            "version": "hyperalpha.ai_trading.gateway_message.v1",
            "signal_version": "hyperalpha.ai_trading.signal_candidate.v1",
            "delivery": "http_json_post",
            "order_authority": "order_backend_only",
        },
        "signal_event_id": 1,
        "strategy_spec_id": 2,
        "user_id": 3,
        "venue": "hyperliquid",
        "symbol": "BTC",
        "exchange_symbol": "BTC",
        "action": "buy",
        "idempotency_key": "signal_event:1",
        "signal_created_at": "2026-06-09T00:00:00+00:00",
        "signal_age_seconds": 12,
        "max_handoff_age_seconds": 900,
        "user_confirmation": {"confirmed": True, "source": "pytest"},
        "market": {"venue": "hyperliquid", "symbol": "BTC"},
        "market_context": {"mark_price": 100000},
        "risk": {"max_loss_pct": 1, "max_leverage": 3},
        "backtest": {
            "status": "passed",
            "accepted_for_handoff": True,
            "metrics": {"trade_count": 42, "max_drawdown": -0.03, "total_return": 0.12},
        },
        "execution_boundary": {
            "signal_only": True,
            "not_an_order": True,
            "requires_user_confirmation": True,
            "ai_may_place_orders": False,
            "order_backend_only": True,
        },
        "validation": {"eligible_for_backend_handoff": True},
        "signal": {
            "symbol": "BTC",
            "action": "buy",
            "idempotency_key": "signal_event:1",
        },
    }


def test_mock_gateway_accepts_valid_signal_contract(tmp_path, monkeypatch):
    log_path = tmp_path / "mock_gateway.jsonl"
    monkeypatch.setattr(mock_gateway, "LOG_PATH", log_path)
    client = TestClient(mock_gateway.app)

    response = client.post("/api/ai-trading/signals", json=_valid_payload())

    assert response.status_code == 202
    assert response.json() == {
        "accepted": True,
        "status": "mock_accepted",
        "signal_event_id": 1,
        "idempotency_key": "signal_event:1",
    }
    assert log_path.exists()
    assert '"idempotency_key": "signal_event:1"' in log_path.read_text()


def test_mock_gateway_rejects_direct_order_boundary(tmp_path, monkeypatch):
    log_path = tmp_path / "mock_gateway.jsonl"
    monkeypatch.setattr(mock_gateway, "LOG_PATH", log_path)
    client = TestClient(mock_gateway.app)
    payload = _valid_payload()
    payload["execution_boundary"]["ai_may_place_orders"] = True
    payload["execution_boundary"]["not_an_order"] = False

    response = client.post("/api/ai-trading/signals", json=payload)

    assert response.status_code == 400
    blockers = response.json()["detail"]["blockers"]
    assert "not_an_order_required" in blockers
    assert "ai_direct_order_must_be_disabled" in blockers
    assert not log_path.exists()

