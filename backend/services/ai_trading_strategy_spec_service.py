"""Structured AI trading strategy spec helpers.

The spec is an execution-preflight contract, not an order instruction. It lets
the frontend and agent agree on symbol, thesis, risk constraints, and missing
approval fields before any downstream signal or order backend is involved.
"""
from __future__ import annotations

import re
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from config.settings import (
    AI_HARD_MAX_LEVERAGE,
    AI_HARD_MAX_ORDER_NOTIONAL_USD,
    AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT,
    AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION,
    AI_HARD_REQUIRE_STOP_LOSS,
    AI_HARD_REQUIRE_TAKE_PROFIT,
)
from database.models import (
    Account,
    AccountProgramBinding,
    AiTradingSignalEventRecord,
    AiTradingSignalHandoffAttemptRecord,
    AiTradingStrategySpecRecord,
    BacktestResult,
    BacktestTriggerLog,
    SignalPool,
    TradingProgram,
)
from services.exchanges.symbol_mapper import SymbolMapper


SPEC_VERSION = "hyperalpha.ai_trading.strategy_spec.v1"
SIGNAL_VERSION = "hyperalpha.ai_trading.signal_candidate.v1"
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
ARCHIVED_STATUS = "archived"
AI_TRADING_V1_MODEL_PROVIDERS = {
    "deepseek",
    "qwen",
}
BACKTEST_HANDOFF_READY_STATUSES = {
    "passed",
    "accepted",
    "approved",
}
BACKTEST_REQUIRED_BLOCKER = "strategy_backtest_required_before_handoff"
BACKTEST_TRADE_COUNT_BLOCKER = "strategy_backtest_trade_count_required"
BACKTEST_MAX_DRAWDOWN_BLOCKER = "strategy_backtest_max_drawdown_required"
BACKTEST_PERFORMANCE_METRIC_BLOCKER = "strategy_backtest_performance_metric_required"
BACKTEST_TRADE_COUNT_METRICS = ("trade_count", "total_trades", "num_trades", "trades")
BACKTEST_MAX_DRAWDOWN_METRICS = ("max_drawdown", "maximum_drawdown", "max_drawdown_pct", "max_dd")
BACKTEST_PERFORMANCE_METRICS = (
    "total_return",
    "return_pct",
    "pnl_pct",
    "net_pnl",
    "sharpe",
    "sortino",
    "win_rate",
    "profit_factor",
)
HIP3_INDEX_SYMBOLS = {
    "SP500",
    "SPX",
    "NASDAQ",
    "NDX",
    "DOW",
    "DJI",
    "XYZ100",
    "GOLD",
    "SILVER",
}
SIGNAL_GATEWAY_ENABLED = os.getenv("AI_TRADING_SIGNAL_GATEWAY_ENABLED", "false").lower() == "true"
SIGNAL_GATEWAY_URL = os.getenv("AI_TRADING_SIGNAL_GATEWAY_URL", "").strip()
SIGNAL_GATEWAY_TIMEOUT_SECONDS = float(os.getenv("AI_TRADING_SIGNAL_GATEWAY_TIMEOUT_SECONDS", "10"))
SIGNAL_GATEWAY_TOKEN = os.getenv("AI_TRADING_SIGNAL_GATEWAY_TOKEN", "").strip()


class SignalGatewayDisabledError(RuntimeError):
    """Raised when signal handoff is requested but the gateway is disabled."""


def _normalize_symbol(symbol: Any) -> str:
    return SymbolMapper.to_internal(str(symbol or "").strip(), "hyperliquid").upper()


def _build_market_identity(symbol: Any) -> Dict[str, Any]:
    raw = str(symbol or "").strip()
    internal_symbol = _normalize_symbol(raw)
    exchange_symbol = SymbolMapper.to_exchange(internal_symbol, "hyperliquid") if internal_symbol else ""

    if ":" in raw:
        dex, display = raw.split(":", 1)
        dex = dex.lower()
        display_symbol = display.upper()
        exchange_symbol = f"{dex}:{display_symbol}"
    elif ":" in exchange_symbol:
        dex, display = exchange_symbol.split(":", 1)
        dex = dex.lower()
        display_symbol = display.upper()
        exchange_symbol = f"{dex}:{display_symbol}"
    else:
        dex = "core"
        display_symbol = internal_symbol
        exchange_symbol = internal_symbol

    if dex == "core":
        category = "crypto"
    elif display_symbol in HIP3_INDEX_SYMBOLS:
        category = "us_index"
    else:
        category = "us_stock"

    return {
        "venue": "hyperliquid",
        "dex": dex,
        "symbol": internal_symbol,
        "exchange_symbol": exchange_symbol,
        "display_symbol": display_symbol,
        "category": category,
    }


def _clean_text(value: Any, max_length: int = 4000) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_length]


def _build_ai_model_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    provider = _clean_text(
        payload.get("model_provider") or payload.get("ai_model_provider"),
        50,
    ).lower()
    model = _clean_text(
        payload.get("model_name") or payload.get("ai_model") or payload.get("model"),
        100,
    )
    source = _clean_text(payload.get("model_source"), 50) or "request"
    return {
        "provider": provider or None,
        "model": model or None,
        "source": source,
        "configured": bool(provider and model),
        "v1_allowed_provider": provider in AI_TRADING_V1_MODEL_PROVIDERS if provider else False,
        "allowed_providers": sorted(AI_TRADING_V1_MODEL_PROVIDERS),
    }


def _default_backtest_gate() -> Dict[str, Any]:
    return {
        "required_before_handoff": True,
        "status": "not_run",
        "accepted_for_handoff": False,
        "backtest_id": None,
        "source": "not_connected",
        "metrics": {},
        "period": {},
        "updated_at": None,
    }


def _normalize_backtest_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    period = payload.get("period") if isinstance(payload.get("period"), dict) else {}
    backtest_id = _clean_text(payload.get("backtest_id") or payload.get("run_id"), 120) or None
    summary = {
        "required_before_handoff": True,
        "status": _clean_text(payload.get("status"), 50).lower() or "unknown",
        "accepted_for_handoff": bool(payload.get("accepted_for_handoff") or payload.get("accepted")),
        "backtest_id": backtest_id,
        "source": _clean_text(payload.get("source"), 50) or "manual",
        "metrics": metrics,
        "period": period,
        "notes": _clean_text(payload.get("notes"), 1000) if payload.get("notes") else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    for key in (
        "program_backtest_result_id",
        "program_binding_id",
        "program_backtest_status",
        "program_backtest_config",
    ):
        if key in payload:
            summary[key] = payload.get(key)
    return summary


def _is_backtest_ready_for_handoff(backtest: Any) -> bool:
    if not isinstance(backtest, dict):
        return False
    if backtest.get("required_before_handoff") is False:
        return True
    status = _clean_text(backtest.get("status"), 50).lower()
    backtest_id = _clean_text(backtest.get("backtest_id") or backtest.get("run_id"), 120)
    return (
        bool(backtest.get("accepted_for_handoff"))
        and status in BACKTEST_HANDOFF_READY_STATUSES
        and bool(backtest_id)
        and not _backtest_metrics_quality_issues(backtest)
    )


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


def _first_metric_float(metrics: Dict[str, Any], keys: tuple[str, ...]) -> Optional[float]:
    for key in keys:
        parsed = _as_float(metrics.get(key))
        if parsed is not None:
            return parsed
    return None


def _backtest_metrics_quality_issues(backtest: Any) -> List[str]:
    metrics = backtest.get("metrics") if isinstance(backtest, dict) else {}
    if not isinstance(metrics, dict):
        metrics = {}

    issues: List[str] = []
    trade_count = _first_metric_float(metrics, BACKTEST_TRADE_COUNT_METRICS)
    if trade_count is None or trade_count <= 0:
        issues.append(BACKTEST_TRADE_COUNT_BLOCKER)

    if _first_metric_float(metrics, BACKTEST_MAX_DRAWDOWN_METRICS) is None:
        issues.append(BACKTEST_MAX_DRAWDOWN_BLOCKER)

    if not any(_first_metric_float(metrics, (key,)) is not None for key in BACKTEST_PERFORMANCE_METRICS):
        issues.append(BACKTEST_PERFORMANCE_METRIC_BLOCKER)

    return issues


def _should_report_backtest_metric_issues(backtest: Any) -> bool:
    if not isinstance(backtest, dict):
        return False
    status = _clean_text(backtest.get("status"), 50).lower()
    metrics = backtest.get("metrics") if isinstance(backtest.get("metrics"), dict) else {}
    return bool(
        backtest.get("accepted_for_handoff")
        or status in BACKTEST_HANDOFF_READY_STATUSES
        or backtest.get("backtest_id")
        or metrics
    )


def _backtest_handoff_blockers(backtest: Any) -> List[str]:
    if _is_backtest_ready_for_handoff(backtest):
        return []
    blockers = [BACKTEST_REQUIRED_BLOCKER]
    if _should_report_backtest_metric_issues(backtest):
        blockers.extend(_backtest_metrics_quality_issues(backtest))
    return list(dict.fromkeys(blockers))


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


def _bias_to_action(bias: Any) -> str:
    normalized = str(bias or "").lower()
    if normalized == "long":
        return "buy"
    if normalized == "short":
        return "sell"
    return "hold"


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


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_loads(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _record_timestamp(value: Any) -> Optional[str]:
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _derive_record_name(spec: Dict[str, Any], name: Optional[str] = None) -> str:
    explicit = _clean_text(name, 120)
    if explicit:
        return explicit
    symbol = _normalize_symbol(spec.get("symbol")) or "Strategy"
    timeframe = str(spec.get("timeframe") or DEFAULT_TIMEFRAME)
    return f"{symbol} {timeframe} AI Trading Spec"[:120]


def serialize_strategy_spec_record(
    record: AiTradingStrategySpecRecord,
    *,
    include_spec: bool = False,
) -> Dict[str, Any]:
    payload = {
        "id": record.id,
        "user_id": record.user_id,
        "name": record.name,
        "symbol": record.symbol,
        "status": record.status,
        "source": record.source,
        "validation": _json_loads(record.validation_json, {}),
        "approved_at": _record_timestamp(record.approved_at),
        "created_at": _record_timestamp(record.created_at),
        "updated_at": _record_timestamp(record.updated_at),
    }
    if include_spec:
        payload["spec"] = _json_loads(record.spec_json, {})
    return payload


def serialize_signal_event_record(
    record: AiTradingSignalEventRecord,
    *,
    include_signal: bool = False,
) -> Dict[str, Any]:
    payload = {
        "id": record.id,
        "user_id": record.user_id,
        "strategy_spec_id": record.strategy_spec_id,
        "symbol": record.symbol,
        "action": record.action,
        "status": record.status,
        "handoff_status": record.handoff_status,
        "error_message": record.error_message,
        "submitted_at": _record_timestamp(record.submitted_at),
        "created_at": _record_timestamp(record.created_at),
        "updated_at": _record_timestamp(record.updated_at),
        "handoff_eligibility": build_signal_event_handoff_eligibility(record),
    }
    if include_signal:
        payload["signal"] = _json_loads(record.signal_json, {})
    return payload


def serialize_signal_handoff_attempt_record(
    record: AiTradingSignalHandoffAttemptRecord,
) -> Dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "signal_event_id": record.signal_event_id,
        "strategy_spec_id": record.strategy_spec_id,
        "symbol": record.symbol,
        "action": record.action,
        "result": record.result,
        "gateway_ready": bool(record.gateway_ready),
        "blockers": _json_loads(record.blockers_json, []),
        "eligibility": _json_loads(record.eligibility_json, {}),
        "error_message": record.error_message,
        "created_at": _record_timestamp(record.created_at),
    }


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
        "ai_model": {
            "allowed_providers": sorted(AI_TRADING_V1_MODEL_PROVIDERS),
            "required_for_live_review": False,
            "stored_fields": ["provider", "model", "source"],
            "secrets_allowed": False,
        },
        "backtest_gate": {
            "required_before_handoff": True,
            "handoff_ready_statuses": sorted(BACKTEST_HANDOFF_READY_STATUSES),
            "required_fields": [
                "backtest_id",
                "status",
                "accepted_for_handoff",
                "metrics.trade_count",
                "metrics.max_drawdown",
                "metrics.performance_metric",
            ],
            "performance_metric_fields": list(BACKTEST_PERFORMANCE_METRICS),
        },
    }


def draft_strategy_spec(payload: Dict[str, Any], *, user_id: int) -> Dict[str, Any]:
    """Build a deterministic structured draft from a user's natural-language idea."""
    text = _clean_text(payload.get("strategy_text") or payload.get("message"))
    symbol = _normalize_symbol(payload.get("symbol"))
    market_identity = _build_market_identity(payload.get("symbol"))
    ai_model = _build_ai_model_config(payload)
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
        "market": market_identity,
        "ai_model": ai_model,
        "backtest": _default_backtest_gate(),
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

    ai_model = spec.get("ai_model") if isinstance(spec.get("ai_model"), dict) else {}
    ai_provider = _clean_text(ai_model.get("provider"), 50).lower()
    ai_model_name = _clean_text(ai_model.get("model"), 100)
    if not ai_provider:
        warnings.append("ai_model_provider_missing")
    elif ai_provider not in AI_TRADING_V1_MODEL_PROVIDERS:
        warnings.append("ai_model_provider_outside_v1")
    if ai_provider and not ai_model_name:
        warnings.append("ai_model_name_missing")
    if any(key in ai_model for key in {"api_key", "secret", "token", "private_key", "password"}):
        issues.append("ai_model_config_must_not_include_secrets")

    backtest = spec.get("backtest") if isinstance(spec.get("backtest"), dict) else _default_backtest_gate()
    warnings.extend(_backtest_handoff_blockers(backtest))

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

    issues = list(dict.fromkeys(issues))
    warnings = list(dict.fromkeys(warnings))
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


def save_strategy_spec_record(
    db: Session,
    *,
    user_id: int,
    spec: Dict[str, Any],
    name: Optional[str] = None,
    source: str = "manual",
) -> AiTradingStrategySpecRecord:
    """Persist a user-owned strategy spec draft/review record."""
    spec_copy = dict(spec or {})
    spec_copy["owner_user_id"] = user_id
    spec_copy.setdefault("version", SPEC_VERSION)
    spec_copy.setdefault("venue", "hyperliquid")
    spec_copy.setdefault("backtest", _default_backtest_gate())

    validation = validate_strategy_spec(spec_copy, user_id=user_id)
    spec_copy["validation"] = {
        "status": validation["status"],
        "issues": validation["issues"],
        "warnings": validation["warnings"],
        "safe_to_emit_signal": validation["safe_to_emit_signal"],
    }

    record = AiTradingStrategySpecRecord(
        user_id=user_id,
        name=_derive_record_name(spec_copy, name),
        symbol=_normalize_symbol(spec_copy.get("symbol")),
        status=validation["status"],
        source=_clean_text(source, 50) or "manual",
        spec_json=_json_dumps(spec_copy),
        validation_json=_json_dumps(validation),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def attach_strategy_backtest_summary(
    db: Session,
    *,
    user_id: int,
    record_id: int,
    summary: Dict[str, Any],
) -> AiTradingStrategySpecRecord:
    """Attach a non-executable backtest summary to a current-user strategy spec."""
    record = get_strategy_spec_record(db, user_id=user_id, record_id=record_id)
    if not record or record.status == ARCHIVED_STATUS:
        raise ValueError("Strategy spec not found")

    spec = _json_loads(record.spec_json, {})
    spec["owner_user_id"] = user_id
    spec.setdefault("version", SPEC_VERSION)
    spec.setdefault("venue", "hyperliquid")
    spec["backtest"] = _normalize_backtest_summary(summary or {})

    validation = validate_strategy_spec(spec, user_id=user_id)
    validation_status = "approved" if record.status == "approved" and validation.get("valid") else validation["status"]
    spec["validation"] = {
        "status": validation_status,
        "issues": validation["issues"],
        "warnings": validation["warnings"],
        "safe_to_emit_signal": validation["safe_to_emit_signal"],
    }
    record.spec_json = _json_dumps(spec)
    record.validation_json = _json_dumps({**validation, "status": validation_status})
    if record.status != "approved" or not validation.get("valid"):
        record.status = validation["status"]
    db.commit()
    db.refresh(record)
    return record


def _get_owned_program_backtest_result(
    db: Session,
    *,
    user_id: int,
    backtest_result_id: int,
) -> Optional[BacktestResult]:
    """Return a Program BacktestResult only when it resolves through current-user ownership."""
    return db.query(BacktestResult).join(
        AccountProgramBinding,
        BacktestResult.binding_id == AccountProgramBinding.id,
    ).join(
        Account,
        AccountProgramBinding.account_id == Account.id,
    ).join(
        TradingProgram,
        AccountProgramBinding.program_id == TradingProgram.id,
    ).filter(
        BacktestResult.id == backtest_result_id,
        BacktestResult.backtest_type == "program",
        BacktestResult.binding_id.isnot(None),
        or_(BacktestResult.user_id == user_id, BacktestResult.user_id.is_(None)),
        AccountProgramBinding.is_deleted != True,
        Account.user_id == user_id,
        Account.is_deleted != True,
        TradingProgram.user_id == user_id,
        TradingProgram.is_deleted != True,
    ).first()


def _program_backtest_result_summary(
    backtest: BacktestResult,
    *,
    accepted_for_handoff: bool,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    status = _clean_text(backtest.status, 50).lower() or "unknown"
    completed = status == "completed"
    config = _json_loads(backtest.config, {}) if isinstance(backtest.config, str) else (backtest.config or {})
    metrics = {
        "total_return": backtest.total_pnl_percent,
        "return_pct": backtest.total_pnl_percent,
        "net_pnl": backtest.total_pnl,
        "max_drawdown": (
            backtest.max_drawdown_percent
            if backtest.max_drawdown_percent is not None
            else backtest.max_drawdown
        ),
        "max_drawdown_percent": backtest.max_drawdown_percent,
        "sharpe": backtest.sharpe_ratio,
        "win_rate": backtest.win_rate,
        "profit_factor": backtest.profit_factor,
        "trade_count": backtest.total_trades,
        "total_trades": backtest.total_trades,
        "winning_trades": backtest.winning_trades,
        "losing_trades": backtest.losing_trades,
        "total_triggers": backtest.total_triggers,
        "initial_balance": backtest.initial_balance,
        "final_equity": backtest.final_equity,
    }
    return {
        "backtest_id": f"program_backtest:{backtest.id}",
        "status": "passed" if completed else status,
        "accepted_for_handoff": bool(accepted_for_handoff and completed),
        "metrics": metrics,
        "period": {
            "start": backtest.start_time.isoformat() if backtest.start_time else None,
            "end": backtest.end_time.isoformat() if backtest.end_time else None,
        },
        "source": "program_backtest_result",
        "notes": notes or (
            "Linked from current-user Program BacktestResult. This is evidence only, not an order."
        ),
        "program_backtest_result_id": backtest.id,
        "program_binding_id": backtest.binding_id,
        "program_backtest_status": status,
        "program_backtest_config": config,
    }


def _program_backtest_symbols(config: Any) -> List[str]:
    config_dict = _json_loads(config, {}) if isinstance(config, str) else (config or {})
    symbols = config_dict.get("symbols") if isinstance(config_dict, dict) else []
    if isinstance(symbols, str):
        symbols = [symbols]
    if not isinstance(symbols, list):
        return []
    return [
        _normalize_symbol(symbol)
        for symbol in symbols
        if _normalize_symbol(symbol)
    ]


def _sample_backtest_equity_curve(equity_curve: Any, *, max_points: int = 100) -> List[Dict[str, Any]]:
    curve = _json_loads(equity_curve, []) if isinstance(equity_curve, str) else (equity_curve or [])
    if not isinstance(curve, list):
        return []

    normalized = [point for point in curve if isinstance(point, dict)]
    if len(normalized) <= max_points:
        return normalized

    step = max(1, len(normalized) // max_points)
    sampled = normalized[::step][:max_points]
    if sampled and sampled[-1] != normalized[-1]:
        sampled[-1] = normalized[-1]
    return sampled


def _program_backtest_result_id_from_summary(backtest: Dict[str, Any]) -> Optional[int]:
    explicit_id = _as_int(backtest.get("program_backtest_result_id"))
    if explicit_id:
        return explicit_id

    raw_backtest_id = _clean_text(backtest.get("backtest_id"), 120)
    if raw_backtest_id.startswith("program_backtest:"):
        return _as_int(raw_backtest_id.split(":", 1)[1])
    return None


def _json_int_list(value: Any) -> List[int]:
    parsed = _json_loads(value, []) if isinstance(value, str) else (value or [])
    if not isinstance(parsed, list):
        return []
    ids: List[int] = []
    for item in parsed:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _signal_pool_symbols(pool: SignalPool) -> List[str]:
    parsed = _json_loads(pool.symbols, []) if isinstance(pool.symbols, str) else (pool.symbols or [])
    if isinstance(parsed, str):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    return [
        _normalize_symbol(symbol)
        for symbol in parsed
        if _normalize_symbol(symbol)
    ]


def _serialize_backtest_binding_candidate(
    db: Session,
    *,
    binding: AccountProgramBinding,
    account: Account,
    program: TradingProgram,
    user_id: int,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    pool_ids = _json_int_list(binding.signal_pool_ids)
    pools: List[SignalPool] = []
    if pool_ids:
        pools = db.query(SignalPool).filter(
            SignalPool.id.in_(pool_ids),
            SignalPool.user_id == user_id,
            SignalPool.is_deleted != True,
        ).all()
    pool_by_id = {pool.id: pool for pool in pools}
    missing_pool_ids = [pool_id for pool_id in pool_ids if pool_id not in pool_by_id]

    symbols: List[str] = []
    pool_names: List[str] = []
    pool_source_types: List[str] = []
    for pool_id in pool_ids:
        pool = pool_by_id.get(pool_id)
        if not pool:
            continue
        pool_names.append(pool.pool_name)
        pool_source_types.append(pool.source_type or "market_signals")
        symbols.extend(_signal_pool_symbols(pool))

    if not symbols and binding.scheduled_trigger_enabled:
        symbols = ["BTC"]
    symbols = list(dict.fromkeys(symbols))

    normalized_symbol = _normalize_symbol(symbol) if symbol else ""
    blockers: List[str] = []
    if binding.exchange != "hyperliquid":
        blockers.append("binding_exchange_must_be_hyperliquid")
    if not binding.is_active:
        blockers.append("binding_inactive")
    if missing_pool_ids:
        blockers.append("signal_pool_missing_or_not_owned")
    if pool_source_types and any(source != "market_signals" for source in pool_source_types):
        blockers.append("signal_pool_source_not_backtestable")
    if not binding.scheduled_trigger_enabled and not pool_ids:
        blockers.append("binding_has_no_backtest_trigger")
    if normalized_symbol and normalized_symbol not in symbols:
        blockers.append("binding_symbol_mismatch")

    return {
        "binding_id": binding.id,
        "account_id": account.id,
        "account_name": account.name,
        "program_id": program.id,
        "program_name": program.name,
        "exchange": binding.exchange or "hyperliquid",
        "is_active": bool(binding.is_active),
        "scheduled_trigger_enabled": bool(binding.scheduled_trigger_enabled),
        "trigger_interval": binding.trigger_interval,
        "signal_pool_ids": pool_ids,
        "signal_pool_names": pool_names,
        "signal_pool_source_types": list(dict.fromkeys(pool_source_types)),
        "symbols": symbols,
        "matches_strategy_symbol": bool(normalized_symbol and normalized_symbol in symbols),
        "eligible": not blockers,
        "blockers": list(dict.fromkeys(blockers)),
    }


def build_strategy_backtest_evidence_detail(
    db: Session,
    *,
    user_id: int,
    record_id: int,
    trigger_limit: int = 25,
) -> Dict[str, Any]:
    """Return non-secret attached Program Backtest evidence for a strategy spec."""
    record = get_strategy_spec_record(db, user_id=user_id, record_id=record_id)
    if not record or record.status == ARCHIVED_STATUS:
        raise ValueError("Strategy spec not found")

    spec = _json_loads(record.spec_json, {})
    backtest_summary = spec.get("backtest") if isinstance(spec.get("backtest"), dict) else {}
    backtest_result_id = _program_backtest_result_id_from_summary(backtest_summary)
    if not backtest_result_id:
        raise ValueError("No Program Backtest evidence attached")

    backtest = _get_owned_program_backtest_result(
        db,
        user_id=user_id,
        backtest_result_id=backtest_result_id,
    )
    if not backtest:
        raise ValueError("Backtest result not found")

    config = _json_loads(backtest.config, {}) if isinstance(backtest.config, str) else (backtest.config or {})
    metrics = {
        "total_return": backtest.total_pnl_percent,
        "return_pct": backtest.total_pnl_percent,
        "net_pnl": backtest.total_pnl,
        "max_drawdown": (
            backtest.max_drawdown_percent
            if backtest.max_drawdown_percent is not None
            else backtest.max_drawdown
        ),
        "max_drawdown_percent": backtest.max_drawdown_percent,
        "sharpe": backtest.sharpe_ratio,
        "win_rate": backtest.win_rate,
        "profit_factor": backtest.profit_factor,
        "trade_count": backtest.total_trades,
        "total_trades": backtest.total_trades,
        "winning_trades": backtest.winning_trades,
        "losing_trades": backtest.losing_trades,
        "total_triggers": backtest.total_triggers,
        "initial_balance": backtest.initial_balance,
        "final_equity": backtest.final_equity,
    }
    evidence_summary = _program_backtest_result_summary(
        backtest,
        accepted_for_handoff=bool(backtest_summary.get("accepted_for_handoff")),
        notes=backtest_summary.get("notes"),
    )

    clamped_limit = max(1, min(int(trigger_limit or 25), 100))
    trigger_query = db.query(BacktestTriggerLog).filter(
        BacktestTriggerLog.backtest_id == backtest.id
    )
    trigger_total = trigger_query.count()
    trigger_rows = trigger_query.order_by(BacktestTriggerLog.trigger_index).limit(clamped_limit).all()
    action_counts = db.query(
        BacktestTriggerLog.decision_action,
        func.count(BacktestTriggerLog.id),
    ).filter(
        BacktestTriggerLog.backtest_id == backtest.id
    ).group_by(BacktestTriggerLog.decision_action).all()
    marker_rows = db.query(
        BacktestTriggerLog.trigger_index,
        BacktestTriggerLog.decision_action,
        BacktestTriggerLog.trigger_type,
    ).filter(
        BacktestTriggerLog.backtest_id == backtest.id,
        BacktestTriggerLog.decision_action != "hold",
    ).order_by(BacktestTriggerLog.trigger_index).limit(clamped_limit).all()

    return {
        "strategy_spec_id": record.id,
        "strategy_symbol": _normalize_symbol(spec.get("symbol") or record.symbol),
        "handoff_ready": _is_backtest_ready_for_handoff(evidence_summary),
        "quality_issues": _backtest_metrics_quality_issues(evidence_summary),
        "attached_summary": backtest_summary,
        "evidence_summary": evidence_summary,
        "backtest_result": {
            "id": backtest.id,
            "status": backtest.status,
            "binding_id": backtest.binding_id,
            "exchange": backtest.exchange or "hyperliquid",
            "symbols": _program_backtest_symbols(config),
            "config": {
                "symbols": config.get("symbols") if isinstance(config, dict) else [],
                "signal_pool_ids": config.get("signal_pool_ids") if isinstance(config, dict) else [],
                "scheduled_interval_sec": config.get("scheduled_interval_sec") if isinstance(config, dict) else None,
                "slippage_percent": config.get("slippage_percent") if isinstance(config, dict) else None,
                "fee_rate": config.get("fee_rate") if isinstance(config, dict) else None,
            },
            "period": {
                "start": backtest.start_time.isoformat() if backtest.start_time else None,
                "end": backtest.end_time.isoformat() if backtest.end_time else None,
            },
            "metrics": metrics,
            "equity_curve_sample": _sample_backtest_equity_curve(backtest.equity_curve),
            "execution_time_ms": backtest.execution_time_ms,
            "created_at": backtest.created_at.isoformat() if backtest.created_at else None,
            "completed_at": backtest.completed_at.isoformat() if backtest.completed_at else None,
        },
        "trigger_summary": {
            "total": trigger_total,
            "returned": len(trigger_rows),
            "limit": clamped_limit,
            "action_counts": {
                str(action or "unknown"): int(count or 0)
                for action, count in action_counts
            },
            "triggers": [
                {
                    "id": trigger.id,
                    "trigger_index": trigger.trigger_index,
                    "trigger_type": trigger.trigger_type,
                    "trigger_time": trigger.trigger_time.isoformat() + "Z" if trigger.trigger_time else None,
                    "symbol": trigger.symbol,
                    "decision_action": trigger.decision_action,
                    "decision_symbol": trigger.decision_symbol,
                    "decision_side": trigger.decision_side,
                    "decision_size": trigger.decision_size,
                    "decision_reason": _clean_text(trigger.decision_reason, 1000),
                    "entry_price": trigger.entry_price,
                    "exit_price": trigger.exit_price,
                    "fee": trigger.fee,
                    "unrealized_pnl": trigger.unrealized_pnl,
                    "realized_pnl": trigger.realized_pnl,
                    "equity_before": trigger.equity_before,
                    "equity_after": trigger.equity_after,
                    "execution_error": _clean_text(trigger.execution_error, 1000) if trigger.execution_error else None,
                }
                for trigger in trigger_rows
            ],
            "markers": [
                {
                    "index": marker.trigger_index,
                    "action": marker.decision_action,
                    "trigger_type": marker.trigger_type,
                }
                for marker in marker_rows
            ],
        },
        "leakage_guard": {
            "program_code_returned": False,
            "credential_fields_returned": False,
            "order_execution_triggered": False,
        },
    }


def serialize_program_backtest_result_candidate(
    backtest: BacktestResult,
    *,
    binding: Optional[AccountProgramBinding] = None,
    account: Optional[Account] = None,
    program: Optional[TradingProgram] = None,
) -> Dict[str, Any]:
    """Serialize a non-secret Program BacktestResult candidate for AI Trading evidence."""
    summary = _program_backtest_result_summary(backtest, accepted_for_handoff=True)
    config = summary.get("program_backtest_config") if isinstance(summary.get("program_backtest_config"), dict) else {}
    return {
        "id": backtest.id,
        "backtest_id": summary.get("backtest_id"),
        "status": _clean_text(backtest.status, 50).lower() or "unknown",
        "source": "program_backtest_result",
        "binding_id": backtest.binding_id,
        "account_id": getattr(account, "id", None),
        "account_name": getattr(account, "name", None),
        "program_id": getattr(program, "id", None),
        "program_name": getattr(program, "name", None),
        "exchange": backtest.exchange or getattr(binding, "exchange", None) or "hyperliquid",
        "symbols": _program_backtest_symbols(config),
        "period": summary.get("period") or {},
        "metrics": summary.get("metrics") or {},
        "handoff_ready": _is_backtest_ready_for_handoff(summary),
        "created_at": _record_timestamp(backtest.created_at),
        "completed_at": _record_timestamp(backtest.completed_at),
    }


def list_program_backtest_result_candidates(
    db: Session,
    *,
    user_id: int,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """List current-user Program BacktestResult rows that can be attached as AI Trading evidence."""
    query = db.query(
        BacktestResult,
        AccountProgramBinding,
        Account,
        TradingProgram,
    ).join(
        AccountProgramBinding,
        BacktestResult.binding_id == AccountProgramBinding.id,
    ).join(
        Account,
        AccountProgramBinding.account_id == Account.id,
    ).join(
        TradingProgram,
        AccountProgramBinding.program_id == TradingProgram.id,
    ).filter(
        BacktestResult.backtest_type == "program",
        BacktestResult.binding_id.isnot(None),
        or_(BacktestResult.user_id == user_id, BacktestResult.user_id.is_(None)),
        AccountProgramBinding.is_deleted != True,
        Account.user_id == user_id,
        Account.is_deleted != True,
        TradingProgram.user_id == user_id,
        TradingProgram.is_deleted != True,
    )
    normalized_status = _clean_text(status, 50).lower()
    if normalized_status:
        query = query.filter(BacktestResult.status == normalized_status)

    row_limit = max(1, min(int(limit or 20), 100))
    fetch_limit = 100 if symbol else row_limit
    rows = query.order_by(
        BacktestResult.completed_at.desc(),
        BacktestResult.created_at.desc(),
        BacktestResult.id.desc(),
    ).limit(fetch_limit).all()

    normalized_symbol = _normalize_symbol(symbol) if symbol else ""
    candidates: List[Dict[str, Any]] = []
    for backtest, binding, account, program in rows:
        if normalized_symbol and normalized_symbol not in _program_backtest_symbols(backtest.config):
            continue
        candidates.append(
            serialize_program_backtest_result_candidate(
                backtest,
                binding=binding,
                account=account,
                program=program,
            )
        )
    return candidates[:row_limit]


def build_strategy_backtest_preflight(
    db: Session,
    *,
    user_id: int,
    record_id: int,
    days: int = 30,
    initial_balance: float = 10000.0,
    slippage_percent: float = 0.05,
    fee_rate: float = 0.035,
) -> Dict[str, Any]:
    """Build a non-executing Program Backtest preflight for an AI Trading strategy spec."""
    record = get_strategy_spec_record(db, user_id=user_id, record_id=record_id)
    if not record or record.status == ARCHIVED_STATUS:
        raise ValueError("Strategy spec not found")

    spec = _json_loads(record.spec_json, {})
    symbol = _normalize_symbol(spec.get("symbol") or record.symbol)
    if not symbol:
        raise ValueError("Strategy spec symbol is required before backtest preflight")

    rows = db.query(
        AccountProgramBinding,
        Account,
        TradingProgram,
    ).join(
        Account,
        AccountProgramBinding.account_id == Account.id,
    ).join(
        TradingProgram,
        AccountProgramBinding.program_id == TradingProgram.id,
    ).filter(
        AccountProgramBinding.is_deleted != True,
        Account.user_id == user_id,
        Account.is_deleted != True,
        TradingProgram.user_id == user_id,
        TradingProgram.is_deleted != True,
    ).order_by(
        AccountProgramBinding.updated_at.desc(),
        AccountProgramBinding.created_at.desc(),
        AccountProgramBinding.id.desc(),
    ).limit(100).all()

    candidates = [
        _serialize_backtest_binding_candidate(
            db,
            binding=binding,
            account=account,
            program=program,
            user_id=user_id,
            symbol=symbol,
        )
        for binding, account, program in rows
    ]
    recommended = next((candidate for candidate in candidates if candidate.get("eligible")), None)

    clamped_days = max(1, min(int(days or 30), 365))
    now = datetime.now(timezone.utc)
    end_time_ms = int(now.timestamp() * 1000)
    start_time_ms = int((now.timestamp() - clamped_days * 24 * 60 * 60) * 1000)
    default_request = None
    if recommended:
        default_request = {
            "binding_id": recommended["binding_id"],
            "start_time_ms": start_time_ms,
            "end_time_ms": end_time_ms,
            "initial_balance": float(initial_balance or 10000.0),
            "slippage_percent": float(slippage_percent),
            "fee_rate": float(fee_rate),
        }

    blockers: List[str] = []
    if not candidates:
        blockers.append("no_program_bindings")
    elif not recommended:
        blockers.append("no_eligible_symbol_matching_program_binding")

    return {
        "strategy_spec_id": record.id,
        "strategy_symbol": symbol,
        "ready": bool(recommended),
        "blockers": blockers,
        "recommended_binding": recommended,
        "candidate_bindings": candidates[:10],
        "program_backtest_endpoint": "/api/programs/backtest",
        "program_backtest_method": "POST",
        "program_backtest_streaming": True,
        "default_request": default_request,
        "assumptions": {
            "days": clamped_days,
            "initial_balance": float(initial_balance or 10000.0),
            "slippage_percent": float(slippage_percent),
            "fee_rate": float(fee_rate),
            "does_not_execute": True,
            "requires_user_confirmation": True,
        },
    }


def attach_strategy_backtest_result(
    db: Session,
    *,
    user_id: int,
    record_id: int,
    backtest_result_id: int,
    accepted_for_handoff: bool = True,
    notes: Optional[str] = None,
) -> AiTradingStrategySpecRecord:
    """Attach an owned Program BacktestResult as non-executable AI Trading evidence."""
    backtest = _get_owned_program_backtest_result(
        db,
        user_id=user_id,
        backtest_result_id=backtest_result_id,
    )
    if not backtest:
        raise ValueError("Backtest result not found")
    summary = _program_backtest_result_summary(
        backtest,
        accepted_for_handoff=accepted_for_handoff,
        notes=_clean_text(notes, 1000) if notes else None,
    )
    return attach_strategy_backtest_summary(
        db,
        user_id=user_id,
        record_id=record_id,
        summary=summary,
    )


def attach_latest_matching_strategy_backtest_result(
    db: Session,
    *,
    user_id: int,
    record_id: int,
    accepted_for_handoff: bool = True,
    notes: Optional[str] = None,
) -> AiTradingStrategySpecRecord:
    """Attach the newest owned, symbol-matching Program BacktestResult evidence."""
    record = get_strategy_spec_record(db, user_id=user_id, record_id=record_id)
    if not record or record.status == ARCHIVED_STATUS:
        raise ValueError("Strategy spec not found")

    spec = _json_loads(record.spec_json, {})
    symbol = _normalize_symbol(spec.get("symbol") or record.symbol)
    if not symbol:
        raise ValueError("Strategy spec symbol is required before attaching backtest evidence")

    candidates = list_program_backtest_result_candidates(
        db,
        user_id=user_id,
        status="completed",
        symbol=symbol,
        limit=20,
    )
    latest_ready = next((candidate for candidate in candidates if candidate.get("handoff_ready")), None)
    if not latest_ready:
        raise ValueError("No handoff-ready Program BacktestResult found for strategy symbol")

    return attach_strategy_backtest_result(
        db,
        user_id=user_id,
        record_id=record_id,
        backtest_result_id=int(latest_ready["id"]),
        accepted_for_handoff=accepted_for_handoff,
        notes=notes or f"Auto-linked latest handoff-ready Program BacktestResult for {symbol}.",
    )


def list_strategy_spec_records(
    db: Session,
    *,
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[AiTradingStrategySpecRecord]:
    query = db.query(AiTradingStrategySpecRecord).filter(
        AiTradingStrategySpecRecord.user_id == user_id,
    )
    if status:
        query = query.filter(AiTradingStrategySpecRecord.status == status)
    else:
        query = query.filter(AiTradingStrategySpecRecord.status != ARCHIVED_STATUS)
    return (
        query
        .order_by(AiTradingStrategySpecRecord.updated_at.desc(), AiTradingStrategySpecRecord.id.desc())
        .limit(max(1, min(int(limit or 50), 100)))
        .all()
    )


def get_strategy_spec_record(
    db: Session,
    *,
    user_id: int,
    record_id: int,
) -> Optional[AiTradingStrategySpecRecord]:
    return db.query(AiTradingStrategySpecRecord).filter(
        AiTradingStrategySpecRecord.id == record_id,
        AiTradingStrategySpecRecord.user_id == user_id,
    ).first()


def approve_strategy_spec_record(
    db: Session,
    *,
    user_id: int,
    record_id: int,
) -> AiTradingStrategySpecRecord:
    """Mark a valid strategy spec approved for later handoff workflows."""
    record = get_strategy_spec_record(db, user_id=user_id, record_id=record_id)
    if not record or record.status == ARCHIVED_STATUS:
        raise ValueError("Strategy spec not found")

    spec = _json_loads(record.spec_json, {})
    validation = validate_strategy_spec(spec, user_id=user_id)
    if not validation.get("valid") or not validation.get("safe_to_emit_signal"):
        record.status = validation["status"]
        record.validation_json = _json_dumps(validation)
        db.commit()
        db.refresh(record)
        raise ValueError("Strategy spec is not valid for approval")

    spec["validation"] = {
        "status": "approved",
        "issues": validation["issues"],
        "warnings": validation["warnings"],
        "safe_to_emit_signal": validation["safe_to_emit_signal"],
    }
    record.status = "approved"
    record.spec_json = _json_dumps(spec)
    record.validation_json = _json_dumps({**validation, "status": "approved"})
    record.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


def archive_strategy_spec_record(
    db: Session,
    *,
    user_id: int,
    record_id: int,
) -> AiTradingStrategySpecRecord:
    record = get_strategy_spec_record(db, user_id=user_id, record_id=record_id)
    if not record:
        raise ValueError("Strategy spec not found")
    record.status = ARCHIVED_STATUS
    db.commit()
    db.refresh(record)
    return record


def build_signal_preview_from_strategy_spec_record(
    record: AiTradingStrategySpecRecord,
    *,
    user_id: int,
    market_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a non-executable signal candidate from an approved strategy spec."""
    if int(record.user_id) != int(user_id):
        raise ValueError("Strategy spec not found")
    if record.status != "approved":
        raise ValueError("Strategy spec must be approved before signal preview")

    spec = _json_loads(record.spec_json, {})
    validation = validate_strategy_spec(spec, user_id=user_id)
    if not validation.get("valid") or not validation.get("safe_to_emit_signal"):
        raise ValueError("Strategy spec is not valid for signal preview")

    market_context = market_context or {}
    market_identity = (
        spec.get("market") if isinstance(spec.get("market"), dict) else _build_market_identity(spec.get("symbol"))
    )
    entry = spec.get("entry") if isinstance(spec.get("entry"), dict) else {}
    exit_rules = spec.get("exit") if isinstance(spec.get("exit"), dict) else {}
    risk = spec.get("risk") if isinstance(spec.get("risk"), dict) else {}
    backtest = spec.get("backtest") if isinstance(spec.get("backtest"), dict) else _default_backtest_gate()
    backtest_ready = _is_backtest_ready_for_handoff(backtest)
    action = _bias_to_action(entry.get("bias"))
    symbol = _normalize_symbol(spec.get("symbol"))

    signal = {
        "version": SIGNAL_VERSION,
        "candidate_type": "review_signal_candidate",
        "strategy_spec_id": record.id,
        "strategy_spec_version": spec.get("version"),
        "venue": "hyperliquid",
        "symbol": symbol,
        "exchange_symbol": market_identity.get("exchange_symbol") or symbol,
        "market": market_identity,
        "ai_model": spec.get("ai_model") if isinstance(spec.get("ai_model"), dict) else {},
        "backtest": backtest,
        "action": action,
        "timeframe": spec.get("timeframe") or DEFAULT_TIMEFRAME,
        "confidence": None,
        "market_context": {
            "mark_price": market_context.get("mark_price"),
            "open_interest": market_context.get("open_interest"),
            "volume_24h_usd": market_context.get("volume_24h_usd"),
            "regime": market_context.get("regime"),
            "source": market_context.get("source") or "user_or_runtime_supplied",
        },
        "risk": {
            "max_loss_pct": risk.get("max_loss_pct"),
            "max_loss_usd": risk.get("max_loss_usd"),
            "max_leverage": risk.get("max_leverage"),
            "position_notional_usd": risk.get("position_notional_usd"),
            "stop_loss": exit_rules.get("stop_loss") if isinstance(exit_rules.get("stop_loss"), dict) else {},
            "take_profit": exit_rules.get("take_profit") if isinstance(exit_rules.get("take_profit"), dict) else {},
            "constraints": risk.get("constraints") or [],
        },
        "decision": {
            "rationale": spec.get("intent") or "",
            "entry_triggers": entry.get("triggers") or [],
            "invalidation": exit_rules.get("invalidation") or [],
            "hold_when": [
                "Current market data is missing or stale.",
                "Stop-loss or take-profit cannot be translated into concrete backend constraints.",
                "The downstream order backend rejects risk or account constraints.",
            ],
        },
        "execution_boundary": {
            "signal_only": True,
            "not_an_order": True,
            "ai_may_place_orders": False,
            "order_backend_only": True,
            "handoff_status": "not_submitted",
            "requires_user_confirmation": True,
        },
        "validation": {
            "status": "ready_for_signal_review",
            "issues": [],
            "warnings": validation.get("warnings", []),
            "eligible_for_backend_handoff": backtest_ready,
        },
        "idempotency_key": f"strategy_spec:{record.id}:signal_preview",
    }

    if not backtest_ready:
        signal["validation"]["warnings"] = list(dict.fromkeys(
            list(signal["validation"]["warnings"]) + _backtest_handoff_blockers(backtest)
        ))

    if action == "hold":
        signal["validation"]["eligible_for_backend_handoff"] = False
        signal["validation"]["warnings"] = list(signal["validation"]["warnings"]) + [
            "entry_bias_does_not_map_to_trade_action"
        ]

    return signal


def create_signal_event_record(
    db: Session,
    *,
    user_id: int,
    strategy_spec_id: int,
    market_context: Optional[Dict[str, Any]] = None,
) -> AiTradingSignalEventRecord:
    """Create a review-only signal candidate audit event from an approved spec."""
    record = get_strategy_spec_record(db, user_id=user_id, record_id=strategy_spec_id)
    if not record:
        raise ValueError("Strategy spec not found")
    signal = build_signal_preview_from_strategy_spec_record(
        record,
        user_id=user_id,
        market_context=market_context,
    )
    event = AiTradingSignalEventRecord(
        user_id=user_id,
        strategy_spec_id=record.id,
        symbol=signal.get("symbol") or record.symbol,
        action=signal.get("action") or "hold",
        status="review_candidate",
        handoff_status=signal.get("execution_boundary", {}).get("handoff_status") or "not_submitted",
        signal_json=_json_dumps(signal),
    )
    db.add(event)
    db.flush()

    signal["signal_event_id"] = event.id
    signal["idempotency_key"] = f"signal_event:{event.id}"
    event.signal_json = _json_dumps(signal)
    db.commit()
    db.refresh(event)
    return event


def list_signal_event_records(
    db: Session,
    *,
    user_id: int,
    strategy_spec_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[AiTradingSignalEventRecord]:
    query = db.query(AiTradingSignalEventRecord).filter(
        AiTradingSignalEventRecord.user_id == user_id,
    )
    if strategy_spec_id is not None:
        query = query.filter(AiTradingSignalEventRecord.strategy_spec_id == strategy_spec_id)
    if status:
        query = query.filter(AiTradingSignalEventRecord.status == status)
    return (
        query
        .order_by(AiTradingSignalEventRecord.created_at.desc(), AiTradingSignalEventRecord.id.desc())
        .limit(max(1, min(int(limit or 50), 100)))
        .all()
    )


def get_signal_event_record(
    db: Session,
    *,
    user_id: int,
    event_id: int,
) -> Optional[AiTradingSignalEventRecord]:
    return db.query(AiTradingSignalEventRecord).filter(
        AiTradingSignalEventRecord.id == event_id,
        AiTradingSignalEventRecord.user_id == user_id,
    ).first()


def _add_signal_handoff_attempt(
    db: Session,
    event: AiTradingSignalEventRecord,
    *,
    result: str,
    eligibility: Dict[str, Any],
    error_message: Optional[str] = None,
) -> AiTradingSignalHandoffAttemptRecord:
    blockers = list(eligibility.get("blockers") or [])
    attempt = AiTradingSignalHandoffAttemptRecord(
        user_id=event.user_id,
        signal_event_id=event.id,
        strategy_spec_id=event.strategy_spec_id,
        symbol=event.symbol,
        action=event.action,
        result=_clean_text(result, 30) or "unknown",
        gateway_ready=bool(eligibility.get("gateway_ready")),
        blockers_json=_json_dumps(blockers),
        eligibility_json=_json_dumps(eligibility),
        error_message=_clean_text(error_message, 2000) if error_message else None,
    )
    db.add(attempt)
    return attempt


def list_signal_handoff_attempt_records(
    db: Session,
    *,
    user_id: int,
    signal_event_id: int,
    limit: int = 20,
) -> List[AiTradingSignalHandoffAttemptRecord]:
    return (
        db.query(AiTradingSignalHandoffAttemptRecord)
        .filter(
            AiTradingSignalHandoffAttemptRecord.user_id == user_id,
            AiTradingSignalHandoffAttemptRecord.signal_event_id == signal_event_id,
        )
        .order_by(
            AiTradingSignalHandoffAttemptRecord.created_at.desc(),
            AiTradingSignalHandoffAttemptRecord.id.desc(),
        )
        .limit(max(1, min(int(limit or 20), 100)))
        .all()
    )


def reject_signal_event_record(
    db: Session,
    *,
    user_id: int,
    event_id: int,
    reason: Optional[str] = None,
) -> AiTradingSignalEventRecord:
    """Mark a review candidate rejected by the user without contacting a gateway."""
    event = get_signal_event_record(db, user_id=user_id, event_id=event_id)
    if not event:
        raise ValueError("Signal event not found")
    if event.status != "review_candidate":
        raise ValueError("Only review_candidate signal events can be rejected")

    signal = _json_loads(event.signal_json, {})
    if not isinstance(signal, dict):
        signal = {}
    now = datetime.now(timezone.utc)
    rejection_reason = _clean_text(reason, 1000) or "Rejected by user before handoff"

    validation = signal.get("validation") if isinstance(signal.get("validation"), dict) else {}
    signal["validation"] = {
        **validation,
        "status": "rejected_by_user",
        "eligible_for_backend_handoff": False,
        "warnings": list(validation.get("warnings") or []) + ["signal_rejected_by_user"],
    }
    execution_boundary = signal.get("execution_boundary") if isinstance(signal.get("execution_boundary"), dict) else {}
    signal["execution_boundary"] = {
        **execution_boundary,
        "handoff_status": "rejected",
    }
    signal["review"] = {
        **(signal.get("review") if isinstance(signal.get("review"), dict) else {}),
        "status": "rejected",
        "reason": rejection_reason,
        "reviewed_at": now.isoformat(),
    }

    event.status = "rejected"
    event.handoff_status = "rejected"
    event.error_message = rejection_reason
    event.signal_json = _json_dumps(signal)
    db.commit()
    db.refresh(event)
    return event


def _build_signal_gateway_payload(event: AiTradingSignalEventRecord) -> Dict[str, Any]:
    signal = _json_loads(event.signal_json, {})
    idempotency_key = signal.get("idempotency_key") if isinstance(signal, dict) else None
    return {
        "type": "AI_TRADING_SIGNAL_CANDIDATE",
        "version": "hyperalpha.ai_trading.gateway_message.v1",
        "signal_event_id": event.id,
        "strategy_spec_id": event.strategy_spec_id,
        "user_id": event.user_id,
        "symbol": event.symbol,
        "action": event.action,
        "idempotency_key": idempotency_key or f"signal_event:{event.id}",
        "signal": signal,
    }


def build_signal_event_handoff_eligibility(event: AiTradingSignalEventRecord) -> Dict[str, Any]:
    """Return a non-secret preflight result for a signal event handoff."""
    blockers: List[str] = []
    gateway_ready = bool(SIGNAL_GATEWAY_ENABLED and SIGNAL_GATEWAY_URL)

    if event.status != "review_candidate":
        blockers.append("event_status_not_review_candidate")
    if event.handoff_status == "submitted":
        blockers.append("handoff_already_submitted")
    if not SIGNAL_GATEWAY_ENABLED:
        blockers.append("gateway_disabled")
    if not SIGNAL_GATEWAY_URL:
        blockers.append("gateway_url_not_configured")

    signal = _json_loads(event.signal_json, {})
    if not isinstance(signal, dict) or not signal:
        blockers.append("signal_payload_missing")
        signal = {}

    validation = signal.get("validation") if isinstance(signal.get("validation"), dict) else {}
    blockers.extend(_backtest_handoff_blockers(signal.get("backtest")))
    if validation.get("eligible_for_backend_handoff") is not True:
        blockers.append("signal_not_eligible_for_backend_handoff")

    execution_boundary = signal.get("execution_boundary") if isinstance(signal.get("execution_boundary"), dict) else {}
    if not execution_boundary:
        blockers.append("execution_boundary_missing")
    if execution_boundary.get("not_an_order") is not True:
        blockers.append("signal_missing_not_an_order_boundary")
    if execution_boundary.get("ai_may_place_orders") is not False:
        blockers.append("signal_allows_direct_ai_order_placement")
    if execution_boundary.get("order_backend_only") is not True:
        blockers.append("signal_missing_order_backend_only_boundary")

    deduped_blockers = list(dict.fromkeys(blockers))
    return {
        "eligible": not deduped_blockers,
        "blockers": deduped_blockers,
        "gateway_ready": gateway_ready,
        "can_retry": event.status == "review_candidate" and event.handoff_status in {"not_submitted", "failed"},
        "default_handoff_status": "available" if gateway_ready else "disabled",
    }


def submit_signal_event_to_gateway(
    db: Session,
    *,
    user_id: int,
    event_id: int,
) -> AiTradingSignalEventRecord:
    """Submit a reviewed signal event to the configured order backend gateway."""
    event = get_signal_event_record(db, user_id=user_id, event_id=event_id)
    if not event:
        raise ValueError("Signal event not found")
    eligibility = build_signal_event_handoff_eligibility(event)
    if not eligibility["eligible"]:
        gateway_blockers = {"gateway_disabled", "gateway_url_not_configured"}
        blockers = list(eligibility.get("blockers") or [])
        non_gateway_blockers = [blocker for blocker in blockers if blocker not in gateway_blockers]
        _add_signal_handoff_attempt(
            db,
            event,
            result="blocked",
            eligibility=eligibility,
            error_message=", ".join(blockers),
        )
        db.commit()
        if non_gateway_blockers:
            raise ValueError(
                "Signal event is not eligible for handoff: "
                + ", ".join(non_gateway_blockers)
            )
        raise SignalGatewayDisabledError("AI Trading signal gateway is disabled")

    signal = _json_loads(event.signal_json, {})
    execution_boundary = signal.get("execution_boundary") if isinstance(signal, dict) else {}
    if not isinstance(execution_boundary, dict):
        execution_boundary = {}

    payload = _build_signal_gateway_payload(event)
    headers = {"Content-Type": "application/json"}
    if SIGNAL_GATEWAY_TOKEN:
        headers["Authorization"] = f"Bearer {SIGNAL_GATEWAY_TOKEN}"

    try:
        response = requests.post(
            SIGNAL_GATEWAY_URL,
            json=payload,
            headers=headers,
            timeout=SIGNAL_GATEWAY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Exception as exc:
        event.handoff_status = "failed"
        event.error_message = str(exc)
        _add_signal_handoff_attempt(
            db,
            event,
            result="failed",
            eligibility=eligibility,
            error_message=str(exc),
        )
        db.commit()
        db.refresh(event)
        raise ValueError(f"Signal gateway handoff failed: {exc}") from exc

    signal["execution_boundary"] = {
        **execution_boundary,
        "handoff_status": "submitted",
    }
    event.status = "submitted"
    event.handoff_status = "submitted"
    event.signal_json = _json_dumps(signal)
    event.error_message = None
    event.submitted_at = datetime.now(timezone.utc)
    _add_signal_handoff_attempt(
        db,
        event,
        result="submitted",
        eligibility=eligibility,
    )
    db.commit()
    db.refresh(event)
    return event


def _summarize_handoff_eligibility(
    events: List[AiTradingSignalEventRecord],
) -> Dict[str, Any]:
    summary = {
        "review_candidates": len(events),
        "eligible": 0,
        "blocked": 0,
        "by_blocker": {},
    }
    for event in events:
        eligibility = build_signal_event_handoff_eligibility(event)
        if eligibility.get("eligible"):
            summary["eligible"] += 1
            continue

        summary["blocked"] += 1
        for blocker in eligibility.get("blockers") or ["unknown_blocker"]:
            summary["by_blocker"][blocker] = summary["by_blocker"].get(blocker, 0) + 1
    return summary


def _summarize_strategy_backtest_evidence(
    records: List[AiTradingStrategySpecRecord],
) -> Dict[str, Any]:
    summary = {
        "total": len(records),
        "ready": 0,
        "blocked": 0,
        "missing": 0,
        "by_blocker": {},
    }
    for record in records:
        spec = _json_loads(record.spec_json, {})
        backtest = spec.get("backtest") if isinstance(spec.get("backtest"), dict) else {}
        blockers = _backtest_handoff_blockers(backtest)
        if not blockers:
            summary["ready"] += 1
            continue

        summary["blocked"] += 1
        backtest_id = _clean_text(backtest.get("backtest_id") or backtest.get("run_id"), 120)
        if not backtest_id:
            summary["missing"] += 1
        for blocker in blockers:
            summary["by_blocker"][blocker] = summary["by_blocker"].get(blocker, 0) + 1
    return summary


def get_ai_trading_runtime_status(db: Session, *, user_id: int) -> Dict[str, Any]:
    """Return non-sensitive AI Trading runtime status for the current user."""
    spec_rows = db.query(
        AiTradingStrategySpecRecord.status,
        func.count(AiTradingStrategySpecRecord.id),
    ).filter(
        AiTradingStrategySpecRecord.user_id == user_id,
    ).group_by(AiTradingStrategySpecRecord.status).all()
    event_rows = db.query(
        AiTradingSignalEventRecord.status,
        func.count(AiTradingSignalEventRecord.id),
    ).filter(
        AiTradingSignalEventRecord.user_id == user_id,
    ).group_by(AiTradingSignalEventRecord.status).all()
    review_candidate_events = db.query(AiTradingSignalEventRecord).filter(
        AiTradingSignalEventRecord.user_id == user_id,
        AiTradingSignalEventRecord.status == "review_candidate",
    ).all()
    spec_records = db.query(AiTradingStrategySpecRecord).filter(
        AiTradingStrategySpecRecord.user_id == user_id,
    ).all()

    spec_counts = {str(status): int(count) for status, count in spec_rows}
    event_counts = {str(status): int(count) for status, count in event_rows}
    return {
        "gateway": {
            "enabled": SIGNAL_GATEWAY_ENABLED,
            "url_configured": bool(SIGNAL_GATEWAY_URL),
            "mode": "http",
            "timeout_seconds": SIGNAL_GATEWAY_TIMEOUT_SECONDS,
            "default_handoff_status": "available" if SIGNAL_GATEWAY_ENABLED and SIGNAL_GATEWAY_URL else "disabled",
        },
        "strategy_specs": {
            "total": sum(spec_counts.values()),
            "by_status": spec_counts,
            "backtest_evidence": _summarize_strategy_backtest_evidence(spec_records),
        },
        "signal_events": {
            "total": sum(event_counts.values()),
            "by_status": event_counts,
            "handoff_eligibility": _summarize_handoff_eligibility(review_candidate_events),
        },
    }
