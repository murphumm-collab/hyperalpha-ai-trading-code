"""Local mock gateway for AI Trading signal handoff acceptance.

Run from backend:

    uv run uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1

Then point the main backend to:

    AI_TRADING_SIGNAL_GATEWAY_ENABLED=true
    AI_TRADING_SIGNAL_GATEWAY_URL=http://127.0.0.1:5621/api/ai-trading/signals

This service never places orders. It only validates the V1 signal gateway
contract and appends accepted payloads to a JSONL audit file.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request


GATEWAY_MESSAGE_TYPE = "AI_TRADING_SIGNAL_CANDIDATE"
GATEWAY_MESSAGE_VERSION = "hyperalpha.ai_trading.gateway_message.v1"
SIGNAL_VERSION = "hyperalpha.ai_trading.signal_candidate.v1"

LOG_PATH = Path(os.getenv("AI_TRADING_MOCK_GATEWAY_LOG", "./logs/ai_trading_mock_gateway.jsonl"))

app = FastAPI(title="HyperAlpha AI Trading Mock Signal Gateway")


def _validate_payload(payload: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    if payload.get("type") != GATEWAY_MESSAGE_TYPE:
        blockers.append("type_mismatch")
    if payload.get("version") != GATEWAY_MESSAGE_VERSION:
        blockers.append("version_mismatch")

    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    if contract.get("signal_version") != SIGNAL_VERSION:
        blockers.append("signal_version_mismatch")
    if contract.get("order_authority") != "order_backend_only":
        blockers.append("order_authority_mismatch")

    if payload.get("venue") != "hyperliquid":
        blockers.append("venue_must_be_hyperliquid")
    if payload.get("action") not in {"buy", "sell"}:
        blockers.append("action_must_be_buy_or_sell")
    if not payload.get("symbol"):
        blockers.append("symbol_required")
    if not payload.get("idempotency_key"):
        blockers.append("idempotency_key_required")

    confirmation = payload.get("user_confirmation") if isinstance(payload.get("user_confirmation"), dict) else {}
    if confirmation.get("confirmed") is not True:
        blockers.append("user_confirmation_required")

    boundary = payload.get("execution_boundary") if isinstance(payload.get("execution_boundary"), dict) else {}
    if boundary.get("signal_only") is not True:
        blockers.append("signal_only_required")
    if boundary.get("not_an_order") is not True:
        blockers.append("not_an_order_required")
    if boundary.get("requires_user_confirmation") is not True:
        blockers.append("requires_user_confirmation_required")
    if boundary.get("ai_may_place_orders") is not False:
        blockers.append("ai_direct_order_must_be_disabled")
    if boundary.get("order_backend_only") is not True:
        blockers.append("order_backend_only_required")

    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    if validation.get("eligible_for_backend_handoff") is not True:
        blockers.append("eligible_for_backend_handoff_required")

    backtest = payload.get("backtest") if isinstance(payload.get("backtest"), dict) else {}
    if backtest.get("accepted_for_handoff") is not True:
        blockers.append("accepted_backtest_required")

    signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
    if signal.get("idempotency_key") != payload.get("idempotency_key"):
        blockers.append("signal_idempotency_key_mismatch")
    if signal.get("symbol") != payload.get("symbol"):
        blockers.append("signal_symbol_mismatch")
    if signal.get("action") != payload.get("action"):
        blockers.append("signal_action_mismatch")

    return blockers


def _append_audit(payload: Dict[str, Any], request: Request) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "client": request.client.host if request.client else None,
        "signal_event_id": payload.get("signal_event_id"),
        "strategy_spec_id": payload.get("strategy_spec_id"),
        "user_id": payload.get("user_id"),
        "symbol": payload.get("symbol"),
        "action": payload.get("action"),
        "idempotency_key": payload.get("idempotency_key"),
        "payload": payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(audit, ensure_ascii=False, sort_keys=True) + "\n")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "ai_trading_mock_signal_gateway",
        "log_path": str(LOG_PATH),
    }


@app.post("/api/ai-trading/signals", status_code=202)
async def receive_signal(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
    blockers = _validate_payload(payload)
    if blockers:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "AI Trading signal gateway contract validation failed",
                "blockers": blockers,
            },
        )

    _append_audit(payload, request)
    return {
        "accepted": True,
        "status": "mock_accepted",
        "signal_event_id": payload.get("signal_event_id"),
        "idempotency_key": payload.get("idempotency_key"),
    }

