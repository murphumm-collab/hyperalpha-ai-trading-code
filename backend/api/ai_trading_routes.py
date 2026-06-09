from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth_utils import get_current_user_dependency
from database.models import User
from services.ai_trading_strategy_spec_service import (
    draft_strategy_spec,
    get_strategy_spec_schema,
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
