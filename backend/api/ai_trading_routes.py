from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_utils import get_current_user_dependency
from database.connection import get_db
from database.models import User
from services.ai_trading_strategy_spec_service import (
    SignalGatewayDisabledError,
    approve_strategy_spec_record,
    archive_strategy_spec_record,
    build_signal_preview_from_strategy_spec_record,
    create_signal_event_record,
    draft_strategy_spec,
    get_ai_trading_runtime_status,
    get_signal_event_record,
    get_strategy_spec_record,
    get_strategy_spec_schema,
    list_signal_handoff_attempt_records,
    list_signal_event_records,
    list_strategy_spec_records,
    reject_signal_event_record,
    save_strategy_spec_record,
    serialize_signal_handoff_attempt_record,
    serialize_signal_event_record,
    serialize_strategy_spec_record,
    submit_signal_event_to_gateway,
    validate_strategy_spec,
)


router = APIRouter(prefix="/api/ai-trading", tags=["AI Trading"])


class StrategySpecDraftRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=64)
    strategy_text: str = Field(..., min_length=1, max_length=6000)
    timeframe: Optional[str] = Field(default=None, max_length=16)
    risk_profile: Optional[str] = Field(default="balanced", max_length=64)
    max_loss_pct: Optional[float] = None
    max_loss_usd: Optional[float] = None
    max_leverage: Optional[int] = None
    position_notional_usd: Optional[float] = None
    stop_loss_rule: Optional[str] = Field(default=None, max_length=1000)
    take_profit_rule: Optional[str] = Field(default=None, max_length=1000)
    require_stop_loss: bool = True
    require_take_profit: bool = True


class StrategySpecValidateRequest(BaseModel):
    spec: Dict[str, Any]


class StrategySpecSaveRequest(BaseModel):
    spec: Dict[str, Any]
    name: Optional[str] = Field(default=None, max_length=120)
    source: Optional[str] = Field(default="manual", max_length=50)


class StrategySignalPreviewRequest(BaseModel):
    market_context: Dict[str, Any] = Field(default_factory=dict)


class SignalEventRejectRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.get("/strategy-spec/schema")
def strategy_spec_schema(
    current_user: User = Depends(get_current_user_dependency),
):
    """Return the AI Trading strategy-spec schema and safety boundary."""
    _ = current_user
    return get_strategy_spec_schema()


@router.get("/runtime")
def ai_trading_runtime_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Return current-user AI Trading runtime status without secrets."""
    return get_ai_trading_runtime_status(db, user_id=current_user.id)


@router.post("/strategy-spec/draft")
def draft_strategy_spec_endpoint(
    request: StrategySpecDraftRequest,
    current_user: User = Depends(get_current_user_dependency),
):
    """Create a structured, non-executable strategy draft for user review."""
    try:
        spec = draft_strategy_spec(_model_dump(request), user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "spec": spec,
        "validation": spec.get("validation", {}),
        "execution_boundary": spec.get("execution", {}),
    }


@router.post("/strategy-spec/validate")
def validate_strategy_spec_endpoint(
    request: StrategySpecValidateRequest,
    current_user: User = Depends(get_current_user_dependency),
):
    """Validate a strategy spec without persisting, signaling, or ordering."""
    validation = validate_strategy_spec(request.spec, user_id=current_user.id)
    return {
        "success": validation.get("valid", False),
        "validation": validation,
    }


@router.get("/strategy-specs")
def list_strategy_specs_endpoint(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """List current-user strategy spec records."""
    records = list_strategy_spec_records(
        db,
        user_id=current_user.id,
        status=status,
        limit=limit,
    )
    return {
        "specs": [
            serialize_strategy_spec_record(record, include_spec=False)
            for record in records
        ]
    }


@router.post("/strategy-specs")
def save_strategy_spec_endpoint(
    request: StrategySpecSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Save a current-user strategy spec draft/review record."""
    record = save_strategy_spec_record(
        db,
        user_id=current_user.id,
        spec=request.spec,
        name=request.name,
        source=request.source or "manual",
    )
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(record, include_spec=True),
    }


@router.get("/strategy-specs/{spec_id}")
def get_strategy_spec_endpoint(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Get a current-user strategy spec record."""
    record = get_strategy_spec_record(db, user_id=current_user.id, record_id=spec_id)
    if not record:
        raise HTTPException(status_code=404, detail="Strategy spec not found")
    return {
        "spec_record": serialize_strategy_spec_record(record, include_spec=True),
    }


@router.post("/strategy-specs/{spec_id}/approve")
def approve_strategy_spec_endpoint(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Approve a valid current-user strategy spec without emitting orders."""
    try:
        record = approve_strategy_spec_record(db, user_id=current_user.id, record_id=spec_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(record, include_spec=True),
    }


@router.delete("/strategy-specs/{spec_id}")
def archive_strategy_spec_endpoint(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Archive a current-user strategy spec record."""
    try:
        record = archive_strategy_spec_record(db, user_id=current_user.id, record_id=spec_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(record, include_spec=False),
    }


@router.post("/strategy-specs/{spec_id}/signal-preview")
def strategy_signal_preview_endpoint(
    spec_id: int,
    request: StrategySignalPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Build a non-executable signal candidate from an approved strategy spec."""
    record = get_strategy_spec_record(db, user_id=current_user.id, record_id=spec_id)
    if not record:
        raise HTTPException(status_code=404, detail="Strategy spec not found")
    try:
        signal_preview = build_signal_preview_from_strategy_spec_record(
            record,
            user_id=current_user.id,
            market_context=request.market_context,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "signal_preview": signal_preview,
    }


@router.post("/strategy-specs/{spec_id}/signal-events")
def create_strategy_signal_event_endpoint(
    spec_id: int,
    request: StrategySignalPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Create a review-only signal candidate audit event from an approved spec."""
    try:
        event = create_signal_event_record(
            db,
            user_id=current_user.id,
            strategy_spec_id=spec_id,
            market_context=request.market_context,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "signal_event": serialize_signal_event_record(event, include_signal=True),
    }


@router.get("/signal-events")
def list_signal_events_endpoint(
    strategy_spec_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """List current-user AI Trading signal candidate events."""
    events = list_signal_event_records(
        db,
        user_id=current_user.id,
        strategy_spec_id=strategy_spec_id,
        status=status,
        limit=limit,
    )
    return {
        "signal_events": [
            serialize_signal_event_record(event, include_signal=False)
            for event in events
        ]
    }


@router.get("/signal-events/{event_id}")
def get_signal_event_endpoint(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Get a current-user AI Trading signal candidate event."""
    event = get_signal_event_record(db, user_id=current_user.id, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Signal event not found")
    return {
        "signal_event": serialize_signal_event_record(event, include_signal=True),
    }


@router.get("/signal-events/{event_id}/handoff-attempts")
def list_signal_event_handoff_attempts_endpoint(
    event_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """List non-secret handoff attempt audit records for a signal event."""
    event = get_signal_event_record(db, user_id=current_user.id, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Signal event not found")
    attempts = list_signal_handoff_attempt_records(
        db,
        user_id=current_user.id,
        signal_event_id=event_id,
        limit=limit,
    )
    return {
        "attempts": [
            serialize_signal_handoff_attempt_record(attempt)
            for attempt in attempts
        ]
    }


@router.post("/signal-events/{event_id}/reject")
def reject_signal_event_endpoint(
    event_id: int,
    request: SignalEventRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Reject a current-user review candidate without contacting the gateway."""
    try:
        event = reject_signal_event_record(
            db,
            user_id=current_user.id,
            event_id=event_id,
            reason=request.reason,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "signal_event": serialize_signal_event_record(event, include_signal=True),
    }


@router.post("/signal-events/{event_id}/handoff")
def submit_signal_event_handoff_endpoint(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Submit a reviewed signal event to the configured external order backend."""
    try:
        event = submit_signal_event_to_gateway(db, user_id=current_user.id, event_id=event_id)
    except SignalGatewayDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "signal_event": serialize_signal_event_record(event, include_signal=True),
    }
