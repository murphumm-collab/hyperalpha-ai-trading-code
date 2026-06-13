import importlib.util
import io
import json
import sys
from pathlib import Path
from urllib import error

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_model_adjust_live_acceptance.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_model_adjust_live_acceptance", SCRIPT_PATH)
live_acceptance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = live_acceptance
SPEC.loader.exec_module(live_acceptance)


def _assert_no_secret_echo(value) -> None:
    rendered = json.dumps(value, ensure_ascii=False).lower() if not isinstance(value, str) else value.lower()
    assert "api_key" not in rendered
    assert "authorization" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "auth.internal" not in rendered


def test_live_model_adjust_acceptance_requires_explicit_confirmation():
    with pytest.raises(RuntimeError, match="--confirm-live-model-call"):
        live_acceptance.run_acceptance(
            base_url="http://127.0.0.1:8802",
            timeout=1,
            symbol="BTC",
            confirm_live_model_call=False,
        )


def test_live_model_adjust_acceptance_rejects_non_local_backend():
    with pytest.raises(RuntimeError, match="base_url must be local"):
        live_acceptance.run_acceptance(
            base_url="https://app.hyperalpha.org",
            timeout=1,
            symbol="BTC",
            confirm_live_model_call=True,
        )


class _FakeApiClient:
    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url
        self.timeout = timeout
        self.session_id = None

    def call(self, method: str, path: str, payload=None):
        if method == "GET" and path == "/runtime":
            return {
                "gateway": {
                    "enabled": True,
                    "target_kind": "local_mock",
                    "runtime_config_blockers": [],
                },
                "agent_sessions": {"total": 2},
            }

        if method == "POST" and path == "/strategy-spec/draft":
            return {
                "spec": {
                    "symbol": payload["symbol"],
                    "timeframe": "15m",
                    "execution": {
                        "signal_only": True,
                        "ai_may_place_orders": False,
                        "order_backend_only": True,
                    },
                    "metadata": {},
                }
            }

        if method == "POST" and path == "/strategy-spec/model-adjust":
            spec = dict(payload["spec"])
            spec["execution"] = {
                "signal_only": True,
                "ai_may_place_orders": False,
                "order_backend_only": True,
            }
            spec["metadata"] = {
                "model_adjustment": {
                    "provider": "qwen",
                    "model": "qwen-plus",
                    "source": "hyper_ai_profile",
                    "rationale": "fake live acceptance response",
                    "risk_notes": ["keep handoff disabled"],
                }
            }
            spec["ai_model"] = {
                "provider": "qwen",
                "model": "qwen-plus",
                "source": "hyper_ai_profile",
                "configured": True,
            }
            return {"spec": spec}

        if method == "POST" and path == "/agent-sessions":
            self.session_id = payload["agent_session_id"]
            return {
                "agent_session": {
                    "id": self.session_id,
                    "name": payload["name"],
                    "context_summary": payload["context_summary"],
                    "status": "active",
                }
            }

        if method == "POST" and path == "/strategy-specs":
            return {
                "spec_record": {
                    "id": 101,
                    "symbol": payload["spec"]["symbol"],
                    "status": "ready_for_review",
                    "agent_session": {
                        "id": payload["agent_session_id"],
                        "name": payload["agent_session_name"],
                    },
                }
            }

        if method == "GET" and path.startswith("/agent-sessions/") and path.endswith("strategy_limit=5&signal_limit=5"):
            return {
                "context": {
                    "agent_session": {
                        "id": self.session_id,
                        "name": "BTC Live Model Adjust Acceptance",
                        "status": "active",
                    },
                    "compression": {
                        "format": "ai_trading_agent_session_context.v1",
                        "scope": "current_user_single_agent_session",
                    },
                    "strategy_specs": [{"id": 101, "symbol": "BTC", "status": "ready_for_review"}],
                    "signal_events": [],
                }
            }

        raise AssertionError(f"unexpected fake API call: {method} {path}")


def test_live_model_adjust_acceptance_happy_path_is_signal_only_and_secret_free(monkeypatch):
    monkeypatch.setattr(live_acceptance, "ApiClient", _FakeApiClient)
    monkeypatch.setattr(live_acceptance.time, "time", lambda: 1780000000)

    report = live_acceptance.run_acceptance(
        base_url="http://127.0.0.1:8802",
        timeout=1,
        symbol="BTC",
        confirm_live_model_call=True,
    )

    rendered = json.dumps(report, sort_keys=True).lower()
    assert report["success"] is True
    assert report["model_adjustment"]["provider"] == "qwen"
    assert report["strategy"]["signal_only"] is True
    assert report["strategy"]["ai_may_place_orders"] is False
    assert report["strategy"]["order_backend_only"] is True
    assert report["session_context"]["strategy_specs"] == 1
    assert report["session_context"]["signal_events"] == 0
    assert report["safety"]["handoff_submitted"] is False
    assert report["safety"]["orders_submitted"] is False
    assert "api_key" not in rendered
    assert "secret" not in rendered
    assert "authorization" not in rendered


def test_live_model_adjust_acceptance_api_client_http_error_is_sanitized(monkeypatch):
    def fake_urlopen(req, timeout):
        raise error.HTTPError(
            req.full_url,
            503,
            "Service Unavailable",
            {},
            io.BytesIO(
                b'{"detail":"api_key=secret Bearer token=secret private_key=secret https://auth.internal"}'
            ),
        )

    monkeypatch.setattr(live_acceptance.request, "urlopen", fake_urlopen)
    client = live_acceptance.ApiClient("http://127.0.0.1:8802/api/ai-trading", timeout=1)

    with pytest.raises(RuntimeError) as exc_info:
        client.call("POST", "/strategy-spec/model-adjust", {"x": 1})

    message = str(exc_info.value)
    assert "POST /strategy-spec/model-adjust -> HTTP 503" in message
    _assert_no_secret_echo(message)


def test_live_model_adjust_acceptance_main_failure_report_is_sanitized(monkeypatch, capsys):
    def failing_run_acceptance(**kwargs):
        raise RuntimeError(
            "api_key=secret Bearer token=secret private_key=secret https://auth.internal"
        )

    monkeypatch.setattr(live_acceptance, "run_acceptance", failing_run_acceptance)
    monkeypatch.setattr(sys, "argv", ["ai_trading_model_adjust_live_acceptance.py", "--confirm-live-model-call"])

    assert live_acceptance.main() == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "success": False,
        "error": live_acceptance.SAFE_ACCEPTANCE_ERROR_MESSAGE,
        "error_type": "RuntimeError",
    }
    _assert_no_secret_echo(payload)
