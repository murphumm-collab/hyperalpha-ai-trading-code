"""Run the AI Trading V1 acceptance flow without a live Postgres/browser stack.

This smoke runner uses FastAPI TestClient, a temporary SQLite database, a
mocked DeepSeek/Qwen model response, and a mocked order-backend gateway. It is
not a production runtime. It proves the API-level V1 flow while local
Postgres/Docker browser acceptance is unavailable.

Run from backend:

    uv run python scripts/ai_trading_v1_acceptance_smoke.py
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import dev_ai_trading_signal_gateway as mock_gateway
import services.ai_trading_strategy_spec_service as strategy_service
from api.ai_trading_routes import router
from api.auth_utils import get_current_user_dependency
from database.connection import Base, get_db
from database.models import User


def _build_client(db_path: Path) -> TestClient:
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    session = session_factory()
    try:
        user = User(username="ai-trading-v1-acceptance", is_active="true")
        session.add(user)
        session.flush()
        user_id = int(user.id)
        session.commit()
    finally:
        session.close()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_dependency] = lambda: SimpleNamespace(id=user_id)
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    client._ai_trading_user_id = user_id
    return client


def _expect_ok(response, *, step: str, status: int = 200) -> Dict[str, Any]:
    if response.status_code != status:
        raise AssertionError(
            f"{step} expected status {status}, got {response.status_code}: {response.text}"
        )
    return response.json()


def _fake_model_config(db, user_id: Optional[int] = None) -> Dict[str, Any]:
    return {
        "configured": True,
        "provider": "qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "api_key": "mock-model-key-not-returned",
        "api_format": "openai",
    }


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"fake response status {self.status_code}")


def _fake_model_post(url: str, headers=None, json=None, timeout=None):
    _ = (url, headers, json, timeout)
    return _FakeResponse({
        "choices": [
            {
                "message": {
                    "content": json_module_dumps({
                        "instruction": (
                            "Use BTC 1h long trend continuation, max leverage 2x, "
                            "max loss 0.5%, stop loss below invalidation, "
                            "take profit near prior high."
                        ),
                        "rationale": "Constrain risk before handoff.",
                        "risk_notes": ["Re-run backtest before any signal handoff."],
                    })
                }
            }
        ]
    })


def json_module_dumps(value: Dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def run_acceptance_smoke() -> Dict[str, Any]:
    original_get_llm_config = strategy_service.get_llm_config
    original_post = strategy_service.requests.post
    original_gateway_enabled = strategy_service.SIGNAL_GATEWAY_ENABLED
    original_gateway_url = strategy_service.SIGNAL_GATEWAY_URL
    original_gateway_token = strategy_service.SIGNAL_GATEWAY_TOKEN

    gateway_calls: List[Dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="ai-trading-v1-") as tmpdir:
        client = _build_client(Path(tmpdir) / "acceptance.db")

        try:
            strategy_service.get_llm_config = _fake_model_config
            strategy_service.requests.post = _fake_model_post

            draft = _expect_ok(client.post(
                "/api/ai-trading/strategy-spec/draft",
                json={
                    "symbol": "BTC",
                    "strategy_text": (
                        "Design a 15m BTC breakout strategy with stop-loss, "
                        "take-profit, max loss, and leverage constraints."
                    ),
                    "timeframe": "15m",
                    "risk_profile": "balanced",
                    "max_loss_pct": 1,
                    "max_leverage": 3,
                    "model_provider": "qwen",
                    "model_name": "qwen-plus",
                    "model_source": "acceptance_smoke",
                },
            ), step="draft strategy")

            model_adjust = _expect_ok(client.post(
                "/api/ai-trading/strategy-spec/model-adjust",
                json={
                    "spec": draft["spec"],
                    "instruction": "Use Qwen to tighten risk and refine the BTC trend setup.",
                    "source": "acceptance_smoke",
                },
            ), step="model adjust strategy")
            adjusted_spec = model_adjust["spec"]
            if adjusted_spec["execution"]["ai_may_place_orders"] is not False:
                raise AssertionError("model-adjust did not preserve no-direct-order boundary")

            saved = _expect_ok(client.post(
                "/api/ai-trading/strategy-specs",
                json={
                    "name": "BTC V1 Acceptance Strategy",
                    "source": "acceptance_smoke",
                    "spec": adjusted_spec,
                },
            ), step="save strategy")
            spec_id = int(saved["spec_record"]["id"])

            backtest = _expect_ok(client.post(
                f"/api/ai-trading/strategy-specs/{spec_id}/backtest-summary",
                json={
                    "backtest_id": f"bt_acceptance_{spec_id}",
                    "status": "passed",
                    "accepted_for_handoff": True,
                    "source": "acceptance_smoke",
                    "metrics": {
                        "total_return": 0.11,
                        "max_drawdown": -0.025,
                        "sharpe": 1.5,
                        "trade_count": 36,
                    },
                    "period": {
                        "start": "2026-01-01",
                        "end": "2026-06-01",
                    },
                },
            ), step="attach backtest")

            approved = _expect_ok(client.post(
                f"/api/ai-trading/strategy-specs/{spec_id}/approve",
            ), step="approve strategy")
            if approved["spec_record"]["status"] != "approved":
                raise AssertionError("strategy was not approved")

            rejected_event = _expect_ok(client.post(
                f"/api/ai-trading/strategy-specs/{spec_id}/signal-events",
                json={"market_context": {"mark_price": 100000, "source": "acceptance_smoke"}},
            ), step="create rejected signal event")["signal_event"]

            rejected = _expect_ok(client.post(
                f"/api/ai-trading/signal-events/{rejected_event['id']}/reject",
                json={"reason": "acceptance smoke rejected one candidate before handoff"},
            ), step="reject signal event")
            if rejected["signal_event"]["handoff_status"] != "rejected":
                raise AssertionError("signal event was not rejected")

            handoff_event = _expect_ok(client.post(
                f"/api/ai-trading/strategy-specs/{spec_id}/signal-events",
                json={"market_context": {"mark_price": 100500, "source": "acceptance_smoke"}},
            ), step="create handoff signal event")["signal_event"]

            def fake_gateway_post(url: str, headers=None, json=None, timeout=None):
                _ = (headers, timeout)
                blockers = mock_gateway._validate_payload(json or {})
                if blockers:
                    return _FakeResponse({"detail": {"blockers": blockers}}, status_code=400)
                gateway_calls.append({"url": url, "payload": json})
                return _FakeResponse({"accepted": True, "status": "mock_accepted"}, status_code=202)

            strategy_service.requests.post = fake_gateway_post
            strategy_service.SIGNAL_GATEWAY_ENABLED = True
            strategy_service.SIGNAL_GATEWAY_URL = "http://mock-order-backend.local/api/ai-trading/signals"
            strategy_service.SIGNAL_GATEWAY_TOKEN = "mock-gateway-token-not-returned"

            handoff = _expect_ok(client.post(
                f"/api/ai-trading/signal-events/{handoff_event['id']}/handoff",
                json={"confirmed_by_user": True, "confirmation_source": "acceptance_smoke"},
            ), step="confirm handoff")
            if handoff["signal_event"]["handoff_status"] != "submitted":
                raise AssertionError("signal event was not submitted")
            if len(gateway_calls) != 1:
                raise AssertionError(f"expected one gateway call, got {len(gateway_calls)}")

            attempts = _expect_ok(client.get(
                f"/api/ai-trading/signal-events/{handoff_event['id']}/handoff-attempts",
            ), step="list handoff attempts")
            if attempts["attempts"][0]["result"] != "submitted":
                raise AssertionError("latest handoff attempt was not submitted")

            runtime = _expect_ok(client.get("/api/ai-trading/runtime"), step="runtime")

            payload = gateway_calls[0]["payload"]
            return {
                "success": True,
                "flow": [
                    "draft",
                    "model_adjust",
                    "save",
                    "attach_backtest",
                    "approve",
                    "create_rejected_signal",
                    "reject_signal",
                    "create_handoff_signal",
                    "confirm_handoff",
                    "audit_attempt",
                    "runtime",
                ],
                "ids": {
                    "user_id": client._ai_trading_user_id,
                    "strategy_spec_id": spec_id,
                    "rejected_signal_event_id": rejected_event["id"],
                    "submitted_signal_event_id": handoff_event["id"],
                },
                "strategy": {
                    "symbol": approved["spec_record"]["symbol"],
                    "status": approved["spec_record"]["status"],
                    "backtest_status": backtest["spec_record"]["spec"]["backtest"]["status"],
                    "backtest_accepted_for_handoff": backtest["spec_record"]["spec"]["backtest"]["accepted_for_handoff"],
                },
                "gateway_contract": {
                    "type": payload["type"],
                    "version": payload["version"],
                    "venue": payload["venue"],
                    "symbol": payload["symbol"],
                    "action": payload["action"],
                    "idempotency_key": payload["idempotency_key"],
                    "signal_only": payload["execution_boundary"]["signal_only"],
                    "not_an_order": payload["execution_boundary"]["not_an_order"],
                    "ai_may_place_orders": payload["execution_boundary"]["ai_may_place_orders"],
                    "accepted_backtest": payload["backtest"]["accepted_for_handoff"],
                },
                "runtime": runtime,
            }
        finally:
            strategy_service.get_llm_config = original_get_llm_config
            strategy_service.requests.post = original_post
            strategy_service.SIGNAL_GATEWAY_ENABLED = original_gateway_enabled
            strategy_service.SIGNAL_GATEWAY_URL = original_gateway_url
            strategy_service.SIGNAL_GATEWAY_TOKEN = original_gateway_token


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Optional path to write the JSON acceptance report.")
    args = parser.parse_args()

    report = run_acceptance_smoke()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
