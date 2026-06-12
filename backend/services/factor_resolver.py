"""
Shared factor resolver for builtin registry factors and custom expression factors.

This module centralizes factor lookup and computation so Prompt, Program,
Signal Detection, and backtest paths stay aligned.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from database.models import CustomFactor
from services.factor_effectiveness_service import factor_effectiveness_service
from services.factor_registry import FACTOR_BY_NAME
from services.factor_expression_engine import factor_expression_engine
from services.technical_indicators import calculate_indicators


def resolve_factor_definition(
    db: Session,
    factor_name: str,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve a factor by name from builtin registry first, then custom_factors."""
    builtin = FACTOR_BY_NAME.get(factor_name)
    if builtin:
        return {
            **builtin,
            "id": None,
            "source": "builtin_registry",
            "expression": builtin.get("expression"),
        }

    custom_query = db.query(CustomFactor).filter(
        CustomFactor.name == factor_name,
        CustomFactor.is_active == True,
    )
    if user_id is not None:
        custom_query = custom_query.filter(or_(
            CustomFactor.user_id == user_id,
            and_(
                CustomFactor.source == "builtin_expression",
                CustomFactor.user_id == None,
            ),
        ))
    else:
        custom_query = custom_query.filter(
            CustomFactor.source == "builtin_expression",
            CustomFactor.user_id == None,
        )
    custom = custom_query.first()
    if not custom:
        return None

    return {
        "name": custom.name,
        "id": custom.id,
        "category": custom.category,
        "description": custom.description or "",
        "expression": custom.expression,
        "source": custom.source or "custom",
        "user_id": custom.user_id,
        "compute_type": "expression",
    }


def compute_factor_series(
    db: Session,
    factor_name: str,
    symbol: str,
    period: str,
    exchange: str,
    klines: List[Dict[str, Any]],
    user_id: Optional[int] = None,
) -> Tuple[Optional[pd.Series], Optional[Dict[str, Any]], Optional[str]]:
    """
    Compute a full factor series for builtin registry factors or custom factors.

    Returns:
        (series, factor_meta, error)
    """
    factor = resolve_factor_definition(db, factor_name, user_id=user_id)
    if not factor:
        return None, None, f"Factor '{factor_name}' not found"

    if factor.get("source") == "builtin_registry":
        indicators: Dict[str, Any] = {}
        if factor.get("compute_type") == "technical":
            indicator_key = factor.get("indicator_key")
            if indicator_key:
                indicators = calculate_indicators(klines, [indicator_key])

        values = factor_effectiveness_service._extract_full_series(
            factor,
            indicators,
            klines,
            len(klines),
            db=db,
            symbol=symbol,
            exchange=exchange,
        )
        if values is None:
            return None, factor, f"Factor '{factor_name}' could not be computed"
        return pd.Series(values), factor, None

    series, err = factor_expression_engine.execute(factor["expression"], klines)
    if series is None or len(series) == 0:
        return None, factor, err or f"Factor '{factor_name}' could not be computed"
    return series, factor, None


def compute_factor_value(
    db: Session,
    factor_name: str,
    symbol: str,
    period: str,
    exchange: str,
    klines: List[Dict[str, Any]],
    user_id: Optional[int] = None,
) -> Tuple[Optional[float], Optional[Dict[str, Any]], Optional[str]]:
    """Compute the latest factor value and return (value, factor_meta, error)."""
    series, factor, err = compute_factor_series(
        db=db,
        factor_name=factor_name,
        symbol=symbol,
        period=period,
        exchange=exchange,
        klines=klines,
        user_id=user_id,
    )
    if series is None:
        return None, factor, err

    last_val = series.iloc[-1]
    if pd.isna(last_val):
        return None, factor, None
    return round(float(last_val), 6), factor, None


def extract_factor_expression(factor: Dict[str, Any]) -> str:
    """Return a human-readable factor expression/label for mixed factor sources."""
    if factor.get("expression"):
        return str(factor["expression"])

    if factor.get("source") == "builtin_registry":
        return str(factor.get("display_name") or factor.get("name") or "")

    return str(factor.get("name") or "")
