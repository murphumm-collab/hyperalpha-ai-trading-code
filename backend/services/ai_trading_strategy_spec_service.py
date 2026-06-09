"""Structured AI trading strategy spec helpers.

The spec is an execution-preflight contract, not an order instruction. It lets
the frontend and agent agree on symbol, thesis, risk constraints, and missing
approval fields before any downstream signal or order backend is involved.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from config.settings import (
    AI_HARD_MAX_LEVERAGE,
    AI_HARD_MAX_ORDER_NOTIONAL_USD,
    AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT,
    AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION,
    AI_HARD_REQUIRE_STOP_LOSS,
    AI_HARD_REQUIRE_TAKE_PROFIT,
)
from services.exchanges.symbol_mapper import SymbolMapper


SPEC_VERSION = "hyperalpha.ai_trading.strategy_spec.v1"
DEFAULT_TIMEFRAME = "15m"
SUPPORTED_TIMEFRAMES = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "8h",
    "12h",
    "1d",
}


def _normalize_symbol(symbol: Any) -> str:
    return SymbolMapper.to_internal(str(symbol or "").strip(), "hyperliquid").upper()


def _clean_text(value: Any, max_length: int = 4000) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_length]


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        parsed = float(value)
        if parsed != parsed:
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_timeframe(text: str, explicit: Any = None) -> str:
    if explicit:
        candidate = str(explicit).strip().lower()
        if candidate in SUPPORTED_TIMEFRAMES:
            return candidate

    match = re.search(r"\b(1m|3m|5m|15m|30m|1h|2h|4h|8h|12h|1d)\b", text.lower())
    if match:
        return match.group(1)
    return DEFAULT_TIMEFRAME


def _detect_bias(text: str) -> str:
    lowered = text.lower()
    long_hits = [
        "long",
        "buy",
        "bullish",
        "做多",
        "看多",
        "买入",
        "多头",
    ]
    short_hits = [
        "short",
        "sell",
        "bearish",
        "做空",
        "看空",
        "卖出",
        "空头",
    ]
    hold_hits = [
        "hold",
        "wait",
        "观望",
        "等待",
        "不交易",
    ]

    has_long = any(item in lowered for item in long_hits)
    has_short = any(item in lowered for item in short_hits)
    has_hold = any(item in lowered for item in hold_hits)
    if has_hold and not (has_long or has_short):
        return "hold"
    if has_long and has_short:
        return "both"
    if has_short:
        return "short"
    if has_long:
        return "long"
    return "undecided"


def _extract_stop_loss_rule(text: str) -> Optional[str]:
    if not text:
        return None
    if re.search(r"(stop[- ]?loss|止损|风控线|invalidation|失效)", text, re.IGNORECASE):
        return "Use the user-described stop-loss or invalidation condition from the strategy text."
    return None


def _extract_take_profit_rule(text: str) -> Optional[str]:
    if not text:
        return None
    if re.search(r"(take[- ]?profit|tp\b|止盈|目标位|profit target|target)", text, re.IGNORECASE):
        return "Use the user-described take-profit or profit-taking condition from the strategy text."
    return None


def _risk_profile_defaults(risk_profile: str) -> Dict[str, Any]:
    profile = str(risk_profile or "balanced").lower()
    if profile in {"conservative", "low", "保守", "稳健"}:
        return {"max_loss_pct": 0.5, "max_leverage": min(2, AI_HARD_MAX_LEVERAGE)}
    if profile in {"aggressive", "high", "激进"}:
        return {"max_loss_pct": 2.0, "max_leverage": min(5, AI_HARD_MAX_LEVERAGE)}
    return {"max_loss_pct": 1.0, "max_leverage": min(3, AI_HARD_MAX_LEVERAGE)}


def _constraint_list(
    *,
    max_loss_pct: Optional[float],
    max_loss_usd: Optional[float],
    max_leverage: Optional[int],
    position_notional_usd: Optional[float],
) -> List[str]:
    constraints = [
        "No live order can be placed by the AI agent directly.",
        "A human user must approve strategy changes before persistence or execution.",
        "The downstream order backend remains the only live execution authority.",
    ]
    if max_loss_pct is not None:
        constraints.append(f"Maximum planned loss per trade: {max_loss_pct:g}%")
    if max_loss_usd is not None:
        constraints.append(f"Maximum planned loss per trade: ${max_loss_usd:g}")
    if max_leverage is not None:
        constraints.append(f"Maximum leverage: {max_leverage}x")
    if position_notional_usd is not None:
        constraints.append(f"Maximum position notional: ${position_notional_usd:g}")
    return constraints


def get_strategy_spec_schema() -> Dict[str, Any]:
    """Return the public strategy-spec contract and platform hard limits."""
    return {
        "version": SPEC_VERSION,
        "venue": "hyperliquid",
        "supported_timeframes": sorted(SUPPORTED_TIMEFRAMES),
        "hard_limits": {
            "max_leverage": AI_HARD_MAX_LEVERAGE,
            "max_single_trade_margin_fraction": AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION,
            "max_projected_margin_usage_percent": AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT,
            "max_order_notional_usd": AI_HARD_MAX_ORDER_NOTIONAL_USD,
            "require_stop_loss": AI_HARD_REQUIRE_STOP_LOSS,
            "require_take_profit": AI_HARD_REQUIRE_TAKE_PROFIT,
        },
        "execution_boundary": {
            "signal_only": True,
            "ai_may_place_orders": False,
            "order_backend_only": True,
            "requires_user_approval": True,
        },
    }


def draft_strategy_spec(payload: Dict[str, Any], *, user_id: int) -> Dict[str, Any]:
    """Build a deterministic structured draft from a user's natural-language idea."""
    text = _clean_text(payload.get("strategy_text") or payload.get("message"))
    symbol = _normalize_symbol(payload.get("symbol"))
    risk_defaults = _risk_profile_defaults(str(payload.get("risk_profile") or "balanced"))

    requested_leverage = _as_int(payload.get("max_leverage"))
    max_leverage = requested_leverage if requested_leverage is not None else risk_defaults["max_leverage"]
    max_leverage = max(1, min(max_leverage, AI_HARD_MAX_LEVERAGE))

    requested_loss_pct = _as_float(payload.get("max_loss_pct"))
    max_loss_pct = requested_loss_pct if requested_loss_pct is not None else risk_defaults["max_loss_pct"]
    max_loss_usd = _as_float(payload.get("max_loss_usd"))
    position_notional_usd = _as_float(payload.get("position_notional_usd"))

    require_stop_loss = bool(payload.get("require_stop_loss", True))
    require_take_profit = bool(payload.get("require_take_profit", True))
    stop_loss_rule = _clean_text(payload.get("stop_loss_rule"), 800) or _extract_stop_loss_rule(text)
    take_profit_rule = _clean_text(payload.get("take_profit_rule"), 800) or _extract_take_profit_rule(text)
    bias = _detect_bias(text)
    timeframe = _extract_timeframe(text, payload.get("timeframe"))

    spec: Dict[str, Any] = {
        "version": SPEC_VERSION,
        "venue": "hyperliquid",
        "owner_user_id": user_id,
        "symbol": symbol,
        "mode": "live_signal_draft",
        "intent": text,
        "timeframe": timeframe,
        "entry": {
            "bias": bias,
            "triggers": [
                "Validate current market data before emitting a signal.",
                "Emit HOLD when entry conditions or risk constraints are incomplete.",
            ],
        },
        "exit": {
            "stop_loss": {
                "required": require_stop_loss,
                "rule": stop_loss_rule,
            },
            "take_profit": {
                "required": require_take_profit,
                "rule": take_profit_rule,
            },
            "invalidation": [
                "Invalidate the setup when the thesis no longer matches current market data.",
            ],
        },
        "risk": {
            "profile": payload.get("risk_profile") or "balanced",
            "max_loss_pct": max_loss_pct,
            "max_loss_usd": max_loss_usd,
            "max_leverage": max_leverage,
            "position_notional_usd": position_notional_usd,
            "platform_hard_max_leverage": AI_HARD_MAX_LEVERAGE,
            "platform_max_single_trade_margin_fraction": AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION,
            "platform_max_projected_margin_usage_percent": AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT,
            "constraints": _constraint_list(
                max_loss_pct=max_loss_pct,
                max_loss_usd=max_loss_usd,
                max_leverage=max_leverage,
                position_notional_usd=position_notional_usd,
            ),
        },
        "execution": {
            "signal_only": True,
            "auto_execution_enabled": False,
            "requires_user_approval": True,
            "ai_may_place_orders": False,
            "order_backend_only": True,
            "handoff": {
                "status": "not_connected",
                "reason": "Strategy draft is not an order and must be reviewed before any backend handoff.",
            },
        },
        "metadata": {
            "source": "natural_language_strategy_draft",
            "generated_by": "hyperalpha_local_spec_builder",
        },
    }

    validation = validate_strategy_spec(spec, user_id=user_id)
    spec["validation"] = {
        "status": validation["status"],
        "issues": validation["issues"],
        "warnings": validation["warnings"],
        "safe_to_emit_signal": validation["safe_to_emit_signal"],
    }
    return spec


def validate_strategy_spec(spec: Dict[str, Any], *, user_id: int) -> Dict[str, Any]:
    """Validate a strategy spec without executing it."""
    issues: List[str] = []
    warnings: List[str] = []

    if not isinstance(spec, dict):
        return {
            "valid": False,
            "status": "rejected",
            "issues": ["spec_must_be_object"],
            "warnings": [],
            "safe_to_emit_signal": False,
        }

    if spec.get("version") != SPEC_VERSION:
        warnings.append("unknown_or_missing_spec_version")
    if spec.get("venue") != "hyperliquid":
        issues.append("venue_must_be_hyperliquid")

    symbol = _normalize_symbol(spec.get("symbol"))
    if not symbol:
        issues.append("symbol_required")

    owner_user_id = spec.get("owner_user_id")
    if owner_user_id is not None:
        try:
            if int(owner_user_id) != int(user_id):
                issues.append("owner_user_id_mismatch")
        except (TypeError, ValueError):
            issues.append("owner_user_id_invalid")

    timeframe = str(spec.get("timeframe") or "").lower()
    if timeframe and timeframe not in SUPPORTED_TIMEFRAMES:
        warnings.append("unsupported_timeframe")

    risk = spec.get("risk") if isinstance(spec.get("risk"), dict) else {}
    max_leverage = _as_int(risk.get("max_leverage"))
    if max_leverage is None or max_leverage < 1:
        issues.append("max_leverage_required")
    elif max_leverage > AI_HARD_MAX_LEVERAGE:
        issues.append(f"max_leverage_exceeds_platform_hard_limit:{max_leverage}>{AI_HARD_MAX_LEVERAGE}")

    max_loss_pct = _as_float(risk.get("max_loss_pct"))
    max_loss_usd = _as_float(risk.get("max_loss_usd"))
    if max_loss_pct is None and max_loss_usd is None:
        issues.append("max_loss_required")
    if max_loss_pct is not None and (max_loss_pct <= 0 or max_loss_pct > 100):
        issues.append("max_loss_pct_out_of_range")
    if max_loss_usd is not None and max_loss_usd <= 0:
        issues.append("max_loss_usd_out_of_range")

    position_notional_usd = _as_float(risk.get("position_notional_usd"))
    if (
        position_notional_usd is not None
        and AI_HARD_MAX_ORDER_NOTIONAL_USD > 0
        and position_notional_usd > AI_HARD_MAX_ORDER_NOTIONAL_USD
    ):
        issues.append(
            "position_notional_exceeds_platform_hard_limit:"
            f"{position_notional_usd}>{AI_HARD_MAX_ORDER_NOTIONAL_USD}"
        )

    exit_rules = spec.get("exit") if isinstance(spec.get("exit"), dict) else {}
    stop_loss = exit_rules.get("stop_loss") if isinstance(exit_rules.get("stop_loss"), dict) else {}
    take_profit = exit_rules.get("take_profit") if isinstance(exit_rules.get("take_profit"), dict) else {}
    stop_loss_required = bool(stop_loss.get("required", AI_HARD_REQUIRE_STOP_LOSS))
    take_profit_required = bool(take_profit.get("required", AI_HARD_REQUIRE_TAKE_PROFIT))

    if stop_loss_required and not stop_loss.get("rule"):
        issues.append("stop_loss_rule_required")
    if take_profit_required and not take_profit.get("rule"):
        issues.append("take_profit_rule_required")
    if not stop_loss_required:
        warnings.append("stop_loss_not_required_by_strategy")
    if not take_profit_required:
        warnings.append("take_profit_not_required_by_strategy")

    execution = spec.get("execution") if isinstance(spec.get("execution"), dict) else {}
    if execution.get("signal_only") is not True:
        issues.append("execution_must_be_signal_only")
    if execution.get("ai_may_place_orders") is not False:
        issues.append("ai_order_placement_must_be_disabled")
    if execution.get("order_backend_only") is not True:
        issues.append("order_backend_only_boundary_required")
    if execution.get("requires_user_approval") is not True:
        issues.append("user_approval_required")
    if execution.get("auto_execution_enabled") is True:
        issues.append("auto_execution_cannot_be_enabled_in_strategy_draft")

    entry = spec.get("entry") if isinstance(spec.get("entry"), dict) else {}
    if entry.get("bias") in {None, "", "undecided"}:
        warnings.append("entry_bias_undecided")

    valid = not issues
    return {
        "valid": valid,
        "status": "ready_for_review" if valid else "needs_user_input",
        "issues": issues,
        "warnings": warnings,
        "safe_to_emit_signal": valid,
        "execution_boundary": {
            "signal_only": True,
            "ai_may_place_orders": False,
            "order_backend_only": True,
            "requires_user_approval": True,
        },
    }
