"""Hard risk validation for automated AI and Program Trader execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from config.settings import (
    AI_HARD_MAX_LEVERAGE,
    AI_HARD_MAX_ORDER_NOTIONAL_USD,
    AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT,
    AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION,
    AI_HARD_REQUIRE_STOP_LOSS,
    AI_HARD_REQUIRE_TAKE_PROFIT,
)


ENTRY_OPERATIONS = {"buy", "sell"}
TRADE_OPERATIONS = {"buy", "sell", "close"}


@dataclass
class RiskValidationResult:
    allowed: bool
    reasons: List[str] = field(default_factory=list)
    projected_margin_usage_percent: Optional[float] = None
    order_notional_usd: Optional[float] = None

    def annotate(self, decision: Any) -> None:
        """Attach risk audit metadata to a dict-like AI decision if possible."""
        if not isinstance(decision, dict):
            return
        if self.allowed:
            decision["_risk_status"] = "accepted"
            if self.projected_margin_usage_percent is not None:
                decision["_projected_margin_usage_percent"] = self.projected_margin_usage_percent
            if self.order_notional_usd is not None:
                decision["_order_notional_usd"] = self.order_notional_usd
            return

        decision["_risk_status"] = "rejected"
        decision["_risk_reasons"] = list(self.reasons)
        if self.projected_margin_usage_percent is not None:
            decision["_projected_margin_usage_percent"] = self.projected_margin_usage_percent
        if self.order_notional_usd is not None:
            decision["_order_notional_usd"] = self.order_notional_usd


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _price_side_errors(
    operation: str,
    market_price: float,
    take_profit_price: Optional[float],
    stop_loss_price: Optional[float],
) -> List[str]:
    reasons: List[str] = []
    tp = _as_float(take_profit_price, 0.0)
    sl = _as_float(stop_loss_price, 0.0)

    if AI_HARD_REQUIRE_TAKE_PROFIT and tp <= 0:
        reasons.append("take_profit_required")
    if AI_HARD_REQUIRE_STOP_LOSS and sl <= 0:
        reasons.append("stop_loss_required")

    if tp > 0:
        if operation == "buy" and tp <= market_price:
            reasons.append("take_profit_must_be_above_entry_for_long")
        elif operation == "sell" and tp >= market_price:
            reasons.append("take_profit_must_be_below_entry_for_short")

    if sl > 0:
        if operation == "buy" and sl >= market_price:
            reasons.append("stop_loss_must_be_below_entry_for_long")
        elif operation == "sell" and sl <= market_price:
            reasons.append("stop_loss_must_be_above_entry_for_short")

    return reasons


def validate_automated_trade_risk(
    *,
    source: str,
    exchange: str,
    account_id: int,
    operation: str,
    symbol: str,
    target_portion_of_balance: Any,
    leverage: Any,
    max_leverage: Any,
    market_price: Any,
    available_balance: Any,
    total_equity: Any,
    margin_usage_percent: Any,
    take_profit_price: Any = None,
    stop_loss_price: Any = None,
) -> RiskValidationResult:
    """Validate an automated trade before exchange order placement.

    This deliberately focuses on hard safety boundaries, not strategy quality.
    Closing positions is kept permissive so high-risk accounts can de-risk.
    """
    operation = str(operation or "").lower()
    symbol = str(symbol or "").upper()
    reasons: List[str] = []

    if operation not in TRADE_OPERATIONS:
        return RiskValidationResult(allowed=True)

    portion = _as_float(target_portion_of_balance)
    lev = _as_int(leverage)
    wallet_max_leverage = _as_int(max_leverage, AI_HARD_MAX_LEVERAGE)
    hard_max_leverage = min(wallet_max_leverage, AI_HARD_MAX_LEVERAGE)
    price = _as_float(market_price)
    available = _as_float(available_balance)
    equity = _as_float(total_equity)
    margin_usage = _as_float(margin_usage_percent)

    if not symbol:
        reasons.append("symbol_required")
    if portion <= 0 or portion > 1:
        reasons.append("target_portion_out_of_range")
    if lev < 1:
        reasons.append("leverage_below_minimum")
    if lev > hard_max_leverage:
        reasons.append(f"leverage_exceeds_hard_max:{lev}>{hard_max_leverage}")
    if price <= 0:
        reasons.append("market_price_required")

    projected_margin_usage: Optional[float] = None
    order_notional: Optional[float] = None

    if operation in ENTRY_OPERATIONS:
        if portion > AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION:
            reasons.append(
                "target_portion_exceeds_hard_max:"
                f"{portion:.4f}>{AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION:.4f}"
            )

        margin = max(available, 0.0) * max(portion, 0.0)
        order_notional = margin * max(lev, 0)
        if equity > 0:
            projected_margin_usage = margin_usage + (margin / equity * 100)
            if projected_margin_usage > AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT:
                reasons.append(
                    "projected_margin_usage_exceeds_hard_max:"
                    f"{projected_margin_usage:.2f}>{AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT:.2f}"
                )

        if AI_HARD_MAX_ORDER_NOTIONAL_USD > 0 and order_notional > AI_HARD_MAX_ORDER_NOTIONAL_USD:
            reasons.append(
                "order_notional_exceeds_hard_max:"
                f"{order_notional:.2f}>{AI_HARD_MAX_ORDER_NOTIONAL_USD:.2f}"
            )

        reasons.extend(
            _price_side_errors(
                operation=operation,
                market_price=price,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
            )
        )

    return RiskValidationResult(
        allowed=not reasons,
        reasons=[
            f"{source}:{exchange}:account={account_id}:{reason}"
            for reason in reasons
        ],
        projected_margin_usage_percent=projected_margin_usage,
        order_notional_usd=order_notional,
    )
