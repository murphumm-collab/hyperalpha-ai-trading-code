from __future__ import annotations

import os
from pathlib import Path as FilesystemPath
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_utils import get_admin_user_dependency, get_current_user_dependency
from database.connection import get_db
from database.models import User
from scripts.ai_trading_v1_completion_audit import (
    build_production_evidence_explain as build_ai_trading_production_evidence_explain,
)
from services.ai_trading_market_universe_service import get_ai_trading_market_universe
from services.ai_trading_production_readiness_service import (
    build_agent_session_context_audit_report,
    build_handoff_attempt_audit_report,
    build_report as build_production_readiness_report,
)
from services.ai_trading_strategy_spec_service import (
    AGENT_CONTEXT_ATTEMPT_MAX_LIMIT,
    AGENT_CONTEXT_SIGNAL_MAX_LIMIT,
    AGENT_CONTEXT_STRATEGY_MAX_LIMIT,
    SignalGatewayDisabledError,
    attach_latest_matching_strategy_backtest_result,
    attach_strategy_backtest_result,
    attach_strategy_backtest_summary,
    adjust_strategy_spec,
    adjust_strategy_spec_record,
    adjust_strategy_spec_record_with_model,
    adjust_strategy_spec_with_model,
    archive_ai_trading_agent_session,
    approve_strategy_spec_record,
    archive_strategy_spec_record,
    build_ai_trading_agent_session_context,
    build_signal_preview_from_strategy_spec_record,
    build_strategy_backtest_evidence_detail,
    build_strategy_backtest_preflight,
    compress_ai_trading_agent_session_context,
    create_ai_trading_agent_session,
    create_signal_event_record,
    draft_strategy_spec,
    get_ai_trading_runtime_status,
    get_signal_event_record,
    get_strategy_spec_record,
    get_strategy_spec_schema,
    list_ai_trading_agent_sessions,
    list_program_backtest_result_candidates,
    list_signal_handoff_attempt_records,
    list_signal_event_records,
    list_strategy_spec_records,
    reject_signal_event_record,
    save_strategy_spec_record,
    serialize_signal_handoff_attempt_record,
    serialize_signal_event_record,
    serialize_signal_preview_payload,
    serialize_ai_trading_agent_session_record,
    serialize_strategy_spec_record,
    submit_signal_event_to_gateway,
    update_ai_trading_agent_session,
    validate_strategy_spec,
)


router = APIRouter(prefix="/api/ai-trading", tags=["AI Trading"])
AI_TRADING_REPO_ROOT = FilesystemPath(__file__).resolve().parents[2]


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
    model_provider: Optional[str] = Field(default=None, max_length=50)
    model_name: Optional[str] = Field(default=None, max_length=100)
    model_source: Optional[str] = Field(default=None, max_length=50)


class StrategySpecValidateRequest(BaseModel):
    spec: Dict[str, Any]


class StrategySpecAdjustRequest(BaseModel):
    spec: Dict[str, Any]
    instruction: str = Field(..., min_length=1, max_length=4000)
    source: Optional[str] = Field(default="natural_language_adjustment", max_length=50)


class StrategySpecModelAdjustRequest(BaseModel):
    spec: Dict[str, Any]
    instruction: str = Field(..., min_length=1, max_length=4000)
    source: Optional[str] = Field(default="model_adjustment", max_length=50)
    agent_session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    )
    agent_session_name: Optional[str] = Field(default=None, max_length=120)
    agent_context_summary: Optional[str] = Field(default=None, max_length=2000)


class StrategySpecRecordAdjustRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=4000)
    source: Optional[str] = Field(default="natural_language_adjustment", max_length=50)


class StrategySpecRecordModelAdjustRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=4000)
    source: Optional[str] = Field(default="model_adjustment", max_length=50)


class StrategySpecSaveRequest(BaseModel):
    spec: Dict[str, Any]
    name: Optional[str] = Field(default=None, max_length=120)
    source: Optional[str] = Field(default="manual", max_length=50)
    agent_session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    )
    agent_session_name: Optional[str] = Field(default=None, max_length=120)
    agent_context_summary: Optional[str] = Field(default=None, max_length=2000)


class AiTradingAgentSessionCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    context_summary: Optional[str] = Field(default=None, max_length=2000)
    agent_session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    )


class AiTradingAgentSessionUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    context_summary: Optional[str] = Field(default=None, max_length=2000)


class StrategySignalPreviewRequest(BaseModel):
    market_context: Dict[str, Any] = Field(default_factory=dict)


class StrategyBacktestSummaryRequest(BaseModel):
    backtest_id: Optional[str] = Field(default=None, max_length=120)
    run_id: Optional[str] = Field(default=None, max_length=120)
    status: str = Field(default="unknown", max_length=50)
    accepted_for_handoff: bool = False
    metrics: Dict[str, Any] = Field(default_factory=dict)
    period: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = Field(default="manual", max_length=50)
    notes: Optional[str] = Field(default=None, max_length=1000)


class StrategyBacktestResultRequest(BaseModel):
    backtest_result_id: int = Field(..., ge=1)
    accepted_for_handoff: bool = True
    notes: Optional[str] = Field(default=None, max_length=1000)


class StrategyLatestBacktestResultRequest(BaseModel):
    accepted_for_handoff: bool = True
    notes: Optional[str] = Field(default=None, max_length=1000)


class StrategyBacktestPreflightRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    initial_balance: float = Field(default=10000.0, gt=0)
    slippage_percent: float = Field(default=0.05, ge=0, le=5)
    fee_rate: float = Field(default=0.035, ge=0, le=5)


class SignalEventRejectRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


class SignalEventHandoffRequest(BaseModel):
    confirmed_by_user: bool = False
    confirmation_source: Optional[str] = Field(default=None, max_length=100)


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


@router.get("/market-universe")
def ai_trading_market_universe_endpoint(
    environment: str = Query("mainnet", pattern="^(mainnet|testnet)$"),
    limit: int = Query(50, ge=1, le=50),
    hip3_dex: str = Query("xyz", min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$"),
    current_user: User = Depends(get_current_user_dependency),
):
    """Return AI Trading Crypto and HIP-3 market-universe presets."""
    _ = current_user
    return get_ai_trading_market_universe(
        environment=environment,
        limit=limit,
        hip3_dex=hip3_dex,
    )


@router.get("/runtime")
def ai_trading_runtime_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Return current-user AI Trading runtime status without secrets."""
    return get_ai_trading_runtime_status(db, user_id=current_user.id)


@router.get("/admin/production-readiness")
def ai_trading_production_readiness_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user_dependency),
):
    """Return admin-only, no-network AI Trading production readiness without secrets."""
    return {
        "success": True,
        "requested_by_user_id": current_user.id,
        "readiness": build_production_readiness_report(
            dict(os.environ),
            handoff_attempt_audit_report=build_handoff_attempt_audit_report(db),
            agent_session_context_audit_report=build_agent_session_context_audit_report(db),
        ),
    }


@router.get("/admin/production-evidence-explain")
def ai_trading_production_evidence_explain_endpoint(
    current_user: User = Depends(get_admin_user_dependency),
):
    """Return admin-only, no-network live-order evidence requirements without secrets."""
    return {
        "success": True,
        "requested_by_user_id": current_user.id,
        "explain": build_ai_trading_production_evidence_explain(AI_TRADING_REPO_ROOT),
    }


@router.get("/agent-sessions")
def list_ai_trading_agent_sessions_endpoint(
    status: Optional[str] = Query(default="active", pattern="^(active|archived)$"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """List current-user AI Trading agent-session partitions."""
    return {
        "agent_sessions": list_ai_trading_agent_sessions(
            db,
            user_id=current_user.id,
            status=status,
            limit=limit,
        ),
    }


@router.post("/agent-sessions")
def create_ai_trading_agent_session_endpoint(
    request: AiTradingAgentSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Create a current-user AI Trading agent session without placing orders."""
    try:
        record = create_ai_trading_agent_session(
            db,
            user_id=current_user.id,
            name=request.name,
            context_summary=request.context_summary,
            agent_session_id=request.agent_session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "agent_session": serialize_ai_trading_agent_session_record(record),
    }


@router.patch("/agent-sessions/{agent_session_id}")
def update_ai_trading_agent_session_endpoint(
    request: AiTradingAgentSessionUpdateRequest,
    agent_session_id: str = Path(
        ...,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Update current-user AI Trading agent-session metadata."""
    try:
        record = update_ai_trading_agent_session(
            db,
            user_id=current_user.id,
            agent_session_id=agent_session_id,
            name=request.name,
            context_summary=request.context_summary,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "agent_session": serialize_ai_trading_agent_session_record(record),
    }


@router.delete("/agent-sessions/{agent_session_id}")
def archive_ai_trading_agent_session_endpoint(
    agent_session_id: str = Path(
        ...,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Archive a current-user AI Trading agent session without deleting audit records."""
    try:
        record = archive_ai_trading_agent_session(
            db,
            user_id=current_user.id,
            agent_session_id=agent_session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "success": True,
        "agent_session": serialize_ai_trading_agent_session_record(record),
    }


@router.get("/agent-sessions/{agent_session_id}/context")
def ai_trading_agent_session_context_endpoint(
    agent_session_id: str = Path(
        ...,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    ),
    strategy_limit: int = Query(default=5, ge=1, le=AGENT_CONTEXT_STRATEGY_MAX_LIMIT),
    signal_limit: int = Query(default=10, ge=1, le=AGENT_CONTEXT_SIGNAL_MAX_LIMIT),
    attempt_limit: int = Query(default=20, ge=1, le=AGENT_CONTEXT_ATTEMPT_MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Return a compact, non-secret context packet for one current-user AI Trading session."""
    try:
        context = build_ai_trading_agent_session_context(
            db,
            user_id=current_user.id,
            agent_session_id=agent_session_id,
            strategy_limit=strategy_limit,
            signal_limit=signal_limit,
            attempt_limit=attempt_limit,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "context": context,
    }


@router.post("/agent-sessions/{agent_session_id}/compress-context")
def compress_ai_trading_agent_session_context_endpoint(
    agent_session_id: str = Path(
        ...,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    ),
    strategy_limit: int = Query(default=10, ge=1, le=AGENT_CONTEXT_STRATEGY_MAX_LIMIT),
    signal_limit: int = Query(default=20, ge=1, le=AGENT_CONTEXT_SIGNAL_MAX_LIMIT),
    attempt_limit: int = Query(default=20, ge=1, le=AGENT_CONTEXT_ATTEMPT_MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Compress and persist a non-secret current-user AI Trading session summary."""
    try:
        result = compress_ai_trading_agent_session_context(
            db,
            user_id=current_user.id,
            agent_session_id=agent_session_id,
            strategy_limit=strategy_limit,
            signal_limit=signal_limit,
            attempt_limit=attempt_limit,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "agent_session": serialize_ai_trading_agent_session_record(result["record"]),
        "context": result["context"],
        "context_summary": result["context_summary"],
    }


@router.get("/backtest-results")
def list_ai_trading_backtest_results_endpoint(
    status: Optional[str] = Query(default=None, max_length=50),
    symbol: Optional[str] = Query(default=None, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """List current-user Program BacktestResult rows attachable as AI Trading evidence."""
    rows = list_program_backtest_result_candidates(
        db,
        user_id=current_user.id,
        status=status,
        symbol=symbol,
        limit=limit,
    )
    return {
        "backtest_results": rows,
    }


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


@router.post("/strategy-spec/adjust")
def adjust_strategy_spec_endpoint(
    request: StrategySpecAdjustRequest,
    current_user: User = Depends(get_current_user_dependency),
):
    """Apply a constrained natural-language strategy adjustment without persisting."""
    try:
        spec = adjust_strategy_spec(
            request.spec,
            instruction=request.instruction,
            user_id=current_user.id,
            source=request.source or "natural_language_adjustment",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "spec": spec,
        "validation": spec.get("validation", {}),
        "execution_boundary": spec.get("execution", {}),
    }


@router.post("/strategy-spec/model-adjust")
def model_adjust_strategy_spec_endpoint(
    request: StrategySpecModelAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Ask the user's configured DeepSeek/Qwen model for a safe adjustment, without persisting."""
    try:
        result = adjust_strategy_spec_with_model(
            db,
            user_id=current_user.id,
            spec=request.spec,
            instruction=request.instruction,
            source=request.source or "model_adjustment",
            agent_session_id=request.agent_session_id,
            agent_session_name=request.agent_session_name,
            agent_context_summary=request.agent_context_summary,
            require_current_user_agent_session=bool(request.agent_session_id),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    spec = result["spec"]
    return {
        "success": True,
        "spec": spec,
        "validation": spec.get("validation", {}),
        "execution_boundary": spec.get("execution", {}),
        "model_context": result.get("model_context", {}),
        "model_suggestion": result.get("model_suggestion", {}),
    }


@router.get("/strategy-specs")
def list_strategy_specs_endpoint(
    status: Optional[str] = None,
    agent_session_id: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    ),
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """List current-user strategy spec records."""
    records = list_strategy_spec_records(
        db,
        user_id=current_user.id,
        status=status,
        agent_session_id=agent_session_id,
        limit=limit,
    )
    return {
        "specs": [
            serialize_strategy_spec_record(
                record,
                include_spec=False,
                db=db,
                user_id=current_user.id,
            )
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
    try:
        record = save_strategy_spec_record(
            db,
            user_id=current_user.id,
            spec=request.spec,
            name=request.name,
            source=request.source or "manual",
            agent_session_id=request.agent_session_id,
            agent_session_name=request.agent_session_name,
            agent_context_summary=request.agent_context_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
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
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/strategy-specs/{spec_id}/adjust")
def adjust_strategy_spec_record_endpoint(
    spec_id: int,
    request: StrategySpecRecordAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Adjust a saved strategy spec and require re-approval/re-backtest before handoff."""
    try:
        record = adjust_strategy_spec_record(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            instruction=request.instruction,
            source=request.source or "natural_language_adjustment",
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/strategy-specs/{spec_id}/model-adjust")
def model_adjust_strategy_spec_record_endpoint(
    spec_id: int,
    request: StrategySpecRecordModelAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Ask the user's configured DeepSeek/Qwen model to adjust a saved spec, then require re-approval."""
    try:
        result = adjust_strategy_spec_record_with_model(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            instruction=request.instruction,
            source=request.source or "model_adjustment",
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(
            result["record"],
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
        "model_context": result.get("model_context", {}),
        "model_suggestion": result.get("model_suggestion", {}),
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
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/strategy-specs/{spec_id}/backtest-summary")
def attach_strategy_backtest_summary_endpoint(
    spec_id: int,
    request: StrategyBacktestSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Attach a current-user backtest summary without emitting signals or orders."""
    try:
        record = attach_strategy_backtest_summary(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            summary=_model_dump(request),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/strategy-specs/{spec_id}/backtest-result")
def attach_strategy_backtest_result_endpoint(
    spec_id: int,
    request: StrategyBacktestResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Attach an owned Program BacktestResult as AI Trading handoff evidence."""
    try:
        record = attach_strategy_backtest_result(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            backtest_result_id=request.backtest_result_id,
            accepted_for_handoff=request.accepted_for_handoff,
            notes=request.notes,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/strategy-specs/{spec_id}/backtest-result/latest")
def attach_latest_strategy_backtest_result_endpoint(
    spec_id: int,
    request: StrategyLatestBacktestResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Attach newest owned symbol-matching Program BacktestResult evidence."""
    try:
        record = attach_latest_matching_strategy_backtest_result(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            accepted_for_handoff=request.accepted_for_handoff,
            notes=request.notes,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/strategy-specs/{spec_id}/backtest-preflight")
def strategy_backtest_preflight_endpoint(
    spec_id: int,
    request: StrategyBacktestPreflightRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Build a non-executing Program Backtest request preflight for a strategy spec."""
    try:
        preflight = build_strategy_backtest_preflight(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            days=request.days,
            initial_balance=request.initial_balance,
            slippage_percent=request.slippage_percent,
            fee_rate=request.fee_rate,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": preflight.get("ready", False),
        "preflight": preflight,
    }


@router.get("/strategy-specs/{spec_id}/backtest-evidence")
def strategy_backtest_evidence_endpoint(
    spec_id: int,
    trigger_limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Return non-secret attached Program Backtest evidence for strategy review."""
    try:
        evidence = build_strategy_backtest_evidence_detail(
            db,
            user_id=current_user.id,
            record_id=spec_id,
            trigger_limit=trigger_limit,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "evidence": evidence,
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
        "spec_record": serialize_strategy_spec_record(
            record,
            include_spec=False,
            db=db,
            user_id=current_user.id,
        ),
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
            db=db,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "signal_preview": serialize_signal_preview_payload(signal_preview),
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
        "signal_event": serialize_signal_event_record(
            event,
            include_signal=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.get("/signal-events")
def list_signal_events_endpoint(
    strategy_spec_id: Optional[int] = None,
    agent_session_id: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,79}$",
    ),
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
        agent_session_id=agent_session_id,
        status=status,
        limit=limit,
    )
    return {
        "signal_events": [
            serialize_signal_event_record(
                event,
                include_signal=False,
                db=db,
                user_id=current_user.id,
            )
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
        "signal_event": serialize_signal_event_record(
            event,
            include_signal=True,
            db=db,
            user_id=current_user.id,
        ),
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
            serialize_signal_handoff_attempt_record(
                attempt,
                db=db,
                user_id=current_user.id,
            )
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
        "signal_event": serialize_signal_event_record(
            event,
            include_signal=True,
            db=db,
            user_id=current_user.id,
        ),
    }


@router.post("/signal-events/{event_id}/handoff")
def submit_signal_event_handoff_endpoint(
    event_id: int,
    request: Optional[SignalEventHandoffRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Submit a reviewed signal event to the configured external order backend."""
    handoff_request = request or SignalEventHandoffRequest()
    try:
        event = submit_signal_event_to_gateway(
            db,
            user_id=current_user.id,
            event_id=event_id,
            confirmed_by_user=handoff_request.confirmed_by_user,
            confirmation_source=handoff_request.confirmation_source,
        )
    except SignalGatewayDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {
        "success": True,
        "signal_event": serialize_signal_event_record(
            event,
            include_signal=True,
            db=db,
            user_id=current_user.id,
        ),
    }
