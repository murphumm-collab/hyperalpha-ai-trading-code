"""Run AI Trading V1 acceptance against the local live backend stack.

This script is for the local LaunchAgent/mock-gateway stack, not production.
It creates audit records in the local database and submits exactly one eligible
signal to the configured local mock signal gateway.

Run from backend:

    uv run python scripts/ai_trading_v1_live_stack_acceptance.py \
      --confirm-local-mock-handoff
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://127.0.0.1:8802"
DEFAULT_MOCK_GATEWAY_HEALTH_URL = "http://127.0.0.1:5621/health"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
SAFE_ACCEPTANCE_ERROR_MESSAGE = "AI Trading live-stack acceptance failed"
SENSITIVE_REPORT_PATTERN = re.compile(
    r"(authorization|bearer|api[_-]?key|private[_-]?key|password|secret|token|https?://[^\s\"'}]+)",
    re.IGNORECASE,
)
SAFE_EXCEPTION_TYPE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,80}$")


@dataclass
class ApiClient:
    base_url: str
    timeout: float

    def call(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        req = request.Request(
            f"{self.base_url.rstrip('/')}{path}",
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as res:
                response_body = res.read().decode("utf-8")
                return json.loads(response_body) if response_body else {}
        except error.HTTPError as exc:
            exc.read()
            raise RuntimeError(f"{method} {path} -> HTTP {exc.code}") from exc
        except error.URLError as exc:
            reason = exc.reason if isinstance(exc.reason, BaseException) else exc
            raise RuntimeError(
                f"{method} {path} request failed: {_safe_exception_type_label(reason)}"
            ) from exc


def _safe_exception_type_label(exc: BaseException) -> str:
    label = exc.__class__.__name__
    if not SAFE_EXCEPTION_TYPE_PATTERN.match(label) or SENSITIVE_REPORT_PATTERN.search(label):
        return "Exception"
    return label


def _safe_error_message(exc: BaseException) -> str:
    message = str(exc).strip()
    if not message or SENSITIVE_REPORT_PATTERN.search(message):
        return SAFE_ACCEPTANCE_ERROR_MESSAGE
    return message[:240]


def _safe_failure_payload(exc: BaseException) -> Dict[str, Any]:
    return {
        "success": False,
        "error": _safe_error_message(exc),
        "error_type": _safe_exception_type_label(exc),
    }


def _json_from_url(url: str, timeout: float) -> Dict[str, Any]:
    with request.urlopen(url, timeout=timeout) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def _host(url: str) -> str:
    return parse.urlparse(url).hostname or ""


def _require_local_url(url: str, *, label: str) -> None:
    host = _host(url)
    if host not in LOCAL_HOSTS:
        raise RuntimeError(f"{label} must be local for this acceptance script, got host={host!r}")


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_acceptance(
    *,
    base_url: str,
    mock_gateway_health_url: str,
    timeout: float,
    symbol: str,
    confirm_local_mock_handoff: bool,
) -> Dict[str, Any]:
    _require_local_url(base_url, label="base_url")
    _require_local_url(mock_gateway_health_url, label="mock_gateway_health_url")
    if not confirm_local_mock_handoff:
        raise RuntimeError(
            "Refusing to submit handoff without --confirm-local-mock-handoff. "
            "This protects against accidentally targeting a real order backend."
        )

    gateway_health = _json_from_url(mock_gateway_health_url, timeout)
    _expect(gateway_health.get("ok") is True, "mock gateway health did not report ok=true")
    _expect(
        gateway_health.get("service") == "ai_trading_mock_signal_gateway",
        "mock gateway health service name did not match ai_trading_mock_signal_gateway",
    )

    client = ApiClient(base_url=f"{base_url.rstrip('/')}/api/ai-trading", timeout=timeout)
    runtime_before = client.call("GET", "/runtime")
    gateway = runtime_before.get("gateway") or {}
    _expect(gateway.get("enabled") is True, "AI Trading signal gateway must be enabled")
    _expect(gateway.get("url_configured") is True, "AI Trading signal gateway URL must be configured")
    _expect(gateway.get("default_handoff_status") == "available", "gateway default status must be available")
    _expect(gateway.get("mode") == "http", "local live-stack acceptance requires runtime gateway mode=http")
    _expect(
        gateway.get("target_kind") == "local_mock",
        "local live-stack acceptance requires runtime gateway target_kind=local_mock",
    )
    _expect(
        not gateway.get("runtime_config_blockers"),
        "runtime gateway config blockers must be empty for local mock acceptance",
    )

    nonce = int(time.time())
    strategy_text = (
        f"15m long breakout strategy for {symbol}: buy only after a confirmed breakout, "
        "use stop-loss below invalidation, take-profit at prior range high, "
        "max loss 0.5%, max leverage 2x, signal only and no direct AI orders."
    )
    draft = client.call(
        "POST",
        "/strategy-spec/draft",
        {
            "symbol": symbol,
            "strategy_text": strategy_text,
            "timeframe": "15m",
            "risk_profile": "balanced",
            "max_loss_pct": 0.5,
            "max_leverage": 2,
            "require_stop_loss": True,
            "require_take_profit": True,
            "model_provider": "qwen",
            "model_name": "qwen-plus",
            "model_source": "local_live_stack_acceptance",
        },
    )
    spec = draft["spec"]
    _expect(spec["entry"]["bias"] == "long", "draft did not create a long/buy strategy")
    _expect(spec["execution"]["signal_only"] is True, "draft did not preserve signal_only")
    _expect(spec["execution"]["ai_may_place_orders"] is False, "draft allowed direct AI orders")

    saved = client.call(
        "POST",
        "/strategy-specs",
        {
            "name": f"{symbol} V1 Live Stack Acceptance {nonce}",
            "source": "local_live_stack_acceptance",
            "spec": spec,
        },
    )
    spec_record = saved["spec_record"]
    spec_id = int(spec_record["id"])

    backtest = client.call(
        "POST",
        f"/strategy-specs/{spec_id}/backtest-summary",
        {
            "backtest_id": f"live-stack-bt-{spec_id}-{nonce}",
            "status": "passed",
            "accepted_for_handoff": True,
            "metrics": {
                "total_return": 0.1,
                "max_drawdown": 0.025,
                "sharpe": 1.8,
                "trade_count": 22,
                "profit_factor": 1.85,
            },
            "period": {"start": "2026-05-01", "end": "2026-06-08"},
            "source": "local_live_stack_acceptance",
        },
    )["spec_record"]
    _expect(backtest["spec"]["backtest"]["accepted_for_handoff"] is True, "backtest was not accepted")

    approved = client.call("POST", f"/strategy-specs/{spec_id}/approve")["spec_record"]
    _expect(approved["status"] == "approved", "strategy was not approved")

    event = client.call(
        "POST",
        f"/strategy-specs/{spec_id}/signal-events",
        {
            "market_context": {
                "mark_price": 100250,
                "regime": "local_live_stack_acceptance",
                "source": "local_live_stack_acceptance",
            }
        },
    )["signal_event"]
    event_id = int(event["id"])
    _expect(event["action"] == "buy", "signal action was not buy")
    _expect(event["signal"]["execution_boundary"]["not_an_order"] is True, "signal became order-like")
    _expect(event["signal"]["execution_boundary"]["ai_may_place_orders"] is False, "signal allowed AI orders")
    _expect(event["handoff_eligibility"]["eligible"] is True, "signal was not eligible before handoff")

    submitted = client.call(
        "POST",
        f"/signal-events/{event_id}/handoff",
        {
            "confirmed_by_user": True,
            "confirmation_source": "local_live_stack_acceptance",
        },
    )["signal_event"]
    _expect(submitted["status"] == "submitted", "submitted signal status mismatch")
    _expect(submitted["handoff_status"] == "submitted", "handoff status mismatch")
    _expect(
        submitted["signal"]["execution_boundary"]["handoff_status"] == "submitted",
        "signal execution boundary handoff_status was not updated",
    )

    attempts = client.call("GET", f"/signal-events/{event_id}/handoff-attempts?limit=5")["attempts"]
    _expect(len(attempts) >= 1, "handoff attempt audit was not persisted")
    latest_attempt = attempts[0]
    _expect(latest_attempt["result"] == "submitted", "latest handoff attempt was not submitted")
    _expect(latest_attempt["gateway_ready"] is True, "latest handoff attempt gateway_ready was false")
    response_summary = (
        (latest_attempt.get("eligibility") or {})
        .get("gateway_response", {})
        .get("response_summary", {})
    )
    _expect(response_summary.get("status") == "mock_accepted", "gateway response did not look like mock gateway")

    runtime_after = client.call("GET", "/runtime")
    return {
        "success": True,
        "base_url": base_url,
        "mock_gateway_health_url": mock_gateway_health_url,
        "ids": {
            "strategy_spec_id": spec_id,
            "signal_event_id": event_id,
        },
        "strategy": {
            "symbol": approved["symbol"],
            "status": approved["status"],
            "backtest_status": approved["spec"]["backtest"]["status"],
            "backtest_accepted_for_handoff": approved["spec"]["backtest"]["accepted_for_handoff"],
        },
        "signal": {
            "action": event["action"],
            "eligible_before_handoff": event["handoff_eligibility"]["eligible"],
            "handoff_status": submitted["handoff_status"],
            "idempotency_key": submitted["signal"]["idempotency_key"],
        },
        "handoff_attempt": {
            "result": latest_attempt["result"],
            "gateway_ready": latest_attempt["gateway_ready"],
            "gateway_response_summary": response_summary,
        },
        "runtime_after": runtime_after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--mock-gateway-health-url", default=DEFAULT_MOCK_GATEWAY_HEALTH_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--symbol", default="BTC")
    parser.add_argument("--confirm-local-mock-handoff", action="store_true")
    args = parser.parse_args()

    try:
        result = run_acceptance(
            base_url=args.base_url,
            mock_gateway_health_url=args.mock_gateway_health_url,
            timeout=args.timeout,
            symbol=args.symbol,
            confirm_local_mock_handoff=args.confirm_local_mock_handoff,
        )
    except Exception as exc:
        print(json.dumps(_safe_failure_payload(exc), ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
