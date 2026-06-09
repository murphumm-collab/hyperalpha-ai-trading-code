"""Run a local live DeepSeek/Qwen model-adjust acceptance check.

This runner targets the local backend only. It is designed for the future
"real user Hyper AI profile/API key" acceptance path without accepting or
printing any model API key itself.

It performs:

    draft -> live model-adjust -> create agent session -> save adjusted spec
    -> load current-user session context

It does not create signal events, submit handoff requests, or place orders.

Run from backend only after configuring a local user's Hyper AI profile:

    uv run python scripts/ai_trading_model_adjust_live_acceptance.py \
      --confirm-live-model-call
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://127.0.0.1:8802"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
SUPPORTED_LIVE_MODEL_PROVIDERS = {"deepseek", "qwen"}
SENSITIVE_REPORT_KEYS = ("api_key", "apikey", "authorization", "password", "private_key", "secret", "token")


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
            response_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} -> {exc.code}: {response_body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"{method} {path} failed: {exc}") from exc


def _host(url: str) -> str:
    return parse.urlparse(url).hostname or ""


def _require_local_url(url: str, *, label: str) -> None:
    host = _host(url)
    if host not in LOCAL_HOSTS:
        raise RuntimeError(f"{label} must be local for this acceptance script, got host={host!r}")


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _contains_sensitive_report_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SENSITIVE_REPORT_KEYS):
                return True
            if _contains_sensitive_report_key(child):
                return True
    if isinstance(value, list):
        return any(_contains_sensitive_report_key(child) for child in value)
    return False


def _provider_from_adjusted_spec(spec: Dict[str, Any]) -> str:
    metadata = spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}
    adjustment = metadata.get("model_adjustment") if isinstance(metadata.get("model_adjustment"), dict) else {}
    provider = adjustment.get("provider")
    if provider:
        return str(provider).lower()
    ai_model = spec.get("ai_model") if isinstance(spec.get("ai_model"), dict) else {}
    return str(ai_model.get("provider") or "").lower()


def run_acceptance(
    *,
    base_url: str,
    timeout: float,
    symbol: str,
    confirm_live_model_call: bool,
) -> Dict[str, Any]:
    _require_local_url(base_url, label="base_url")
    if not confirm_live_model_call:
        raise RuntimeError(
            "Refusing to call a live DeepSeek/Qwen model without --confirm-live-model-call. "
            "Configure the local user's Hyper AI profile first; this script never accepts API keys."
        )

    client = ApiClient(base_url=f"{base_url.rstrip('/')}/api/ai-trading", timeout=timeout)
    runtime_before = client.call("GET", "/runtime")

    nonce = int(time.time())
    strategy_text = (
        f"Design a {symbol} 15m signal-only breakout strategy. "
        "Keep risk bounded with stop-loss, take-profit, max loss, and leverage constraints. "
        "Return HOLD if data or risk conditions are incomplete. Do not place orders."
    )
    draft = client.call(
        "POST",
        "/strategy-spec/draft",
        {
            "symbol": symbol,
            "strategy_text": strategy_text,
            "timeframe": "15m",
            "risk_profile": "balanced",
            "max_loss_pct": 1,
            "max_leverage": 3,
            "require_stop_loss": True,
            "require_take_profit": True,
            "model_source": "live_model_adjust_acceptance",
        },
    )
    spec = draft["spec"]
    _expect(spec["execution"]["signal_only"] is True, "draft did not preserve signal_only")
    _expect(spec["execution"]["ai_may_place_orders"] is False, "draft allowed direct AI orders")
    _expect(spec["execution"]["order_backend_only"] is True, "draft did not preserve order_backend_only")

    model_adjust = client.call(
        "POST",
        "/strategy-spec/model-adjust",
        {
            "spec": spec,
            "instruction": (
                "Use the configured DeepSeek/Qwen profile to refine entries, exits, TP/SL, "
                "max loss, leverage, and any missing confirmations. Preserve signal-only "
                "execution and do not create orders."
            ),
            "source": "live_model_adjust_acceptance",
        },
    )
    adjusted_spec = model_adjust["spec"]
    provider = _provider_from_adjusted_spec(adjusted_spec)
    _expect(provider in SUPPORTED_LIVE_MODEL_PROVIDERS, f"model-adjust provider must be DeepSeek/Qwen, got {provider!r}")
    _expect(adjusted_spec["execution"]["signal_only"] is True, "model-adjust removed signal_only")
    _expect(adjusted_spec["execution"]["ai_may_place_orders"] is False, "model-adjust allowed direct AI orders")
    _expect(adjusted_spec["execution"]["order_backend_only"] is True, "model-adjust removed order_backend_only")

    session = client.call(
        "POST",
        "/agent-sessions",
        {
            "name": f"{symbol} Live Model Adjust Acceptance {nonce}",
            "context_summary": "live model-adjust acceptance; signal-only; no handoff; no orders",
            "agent_session_id": f"ait:model:{symbol.lower()}:{nonce}",
        },
    )["agent_session"]

    saved = client.call(
        "POST",
        "/strategy-specs",
        {
            "name": f"{symbol} Live Model Adjust Acceptance {nonce}",
            "source": "live_model_adjust_acceptance",
            "spec": adjusted_spec,
            "agent_session_id": session["id"],
            "agent_session_name": session["name"],
            "agent_context_summary": session.get("context_summary"),
        },
    )["spec_record"]

    context = client.call(
        "GET",
        f"/agent-sessions/{parse.quote(session['id'], safe='')}/context?strategy_limit=5&signal_limit=5",
    )["context"]
    _expect(context["agent_session"]["id"] == session["id"], "session context id mismatch")
    _expect(len(context.get("strategy_specs") or []) >= 1, "session context did not include the saved strategy")
    _expect(not context.get("signal_events"), "live model-adjust acceptance should not create signal events")

    report = {
        "success": True,
        "base_url": base_url,
        "flow": [
            "runtime",
            "draft",
            "live_model_adjust",
            "create_agent_session",
            "save_adjusted_spec",
            "load_agent_session_context",
        ],
        "ids": {
            "agent_session_id": session["id"],
            "strategy_spec_id": saved["id"],
        },
        "model_adjustment": {
            "provider": provider,
            "model": (
                adjusted_spec.get("metadata", {})
                .get("model_adjustment", {})
                .get("model")
            ),
            "source": "hyper_ai_profile",
        },
        "strategy": {
            "symbol": saved["symbol"],
            "status": saved["status"],
            "signal_only": adjusted_spec["execution"]["signal_only"],
            "ai_may_place_orders": adjusted_spec["execution"]["ai_may_place_orders"],
            "order_backend_only": adjusted_spec["execution"]["order_backend_only"],
        },
        "session_context": {
            "format": context.get("compression", {}).get("format"),
            "strategy_specs": len(context.get("strategy_specs") or []),
            "signal_events": len(context.get("signal_events") or []),
        },
        "runtime_before": {
            "gateway": runtime_before.get("gateway", {}),
            "agent_sessions": runtime_before.get("agent_sessions", {}),
        },
        "safety": {
            "signal_events_created": 0,
            "handoff_submitted": False,
            "orders_submitted": False,
            "credential_argument_supported": False,
        },
    }
    _expect(not _contains_sensitive_report_key(report), "acceptance report contains a sensitive key name")
    _expect("api_key" not in _safe_json(report).lower(), "acceptance report leaked api_key text")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--symbol", default="BTC")
    parser.add_argument("--confirm-live-model-call", action="store_true")
    args = parser.parse_args()

    try:
        result = run_acceptance(
            base_url=args.base_url,
            timeout=args.timeout,
            symbol=args.symbol,
            confirm_live_model_call=args.confirm_live_model_call,
        )
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
