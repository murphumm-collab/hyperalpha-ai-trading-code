import importlib.util
import io
import json
import sys
from pathlib import Path
from urllib import error

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_v1_live_stack_acceptance.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_live_stack_acceptance", SCRIPT_PATH)
live_acceptance = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
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


def test_live_stack_acceptance_requires_explicit_local_mock_confirmation():
    with pytest.raises(RuntimeError, match="--confirm-local-mock-handoff"):
        live_acceptance.run_acceptance(
            base_url="http://127.0.0.1:8802",
            mock_gateway_health_url="http://127.0.0.1:5621/health",
            timeout=1,
            symbol="BTC",
            confirm_local_mock_handoff=False,
        )


def test_live_stack_acceptance_rejects_non_local_backend_url():
    with pytest.raises(RuntimeError, match="base_url must be local"):
        live_acceptance.run_acceptance(
            base_url="https://orders.hyperalpha.org",
            mock_gateway_health_url="http://127.0.0.1:5621/health",
            timeout=1,
            symbol="BTC",
            confirm_local_mock_handoff=True,
        )


def test_live_stack_acceptance_rejects_external_runtime_gateway(monkeypatch):
    monkeypatch.setattr(
        live_acceptance,
        "_json_from_url",
        lambda url, timeout: {"ok": True, "service": "ai_trading_mock_signal_gateway"},
    )

    calls = []

    def fake_call(self, method, path, payload=None):
        calls.append((method, path, payload))
        if path == "/runtime":
            return {
                "gateway": {
                    "enabled": True,
                    "url_configured": True,
                    "mode": "http",
                    "default_handoff_status": "available",
                    "target_kind": "external_order_backend",
                    "runtime_config_blockers": [],
                }
            }
        raise AssertionError("live-stack acceptance should stop before drafting a strategy")

    monkeypatch.setattr(live_acceptance.ApiClient, "call", fake_call)

    with pytest.raises(AssertionError, match="target_kind=local_mock"):
        live_acceptance.run_acceptance(
            base_url="http://127.0.0.1:8802",
            mock_gateway_health_url="http://127.0.0.1:5621/health",
            timeout=1,
            symbol="BTC",
            confirm_local_mock_handoff=True,
        )

    assert calls == [
        (
            "GET",
            "/runtime",
            None,
        )
    ]


def test_live_stack_acceptance_rejects_unsupported_runtime_gateway_mode(monkeypatch):
    monkeypatch.setattr(
        live_acceptance,
        "_json_from_url",
        lambda url, timeout: {"ok": True, "service": "ai_trading_mock_signal_gateway"},
    )

    calls = []

    def fake_call(self, method, path, payload=None):
        calls.append((method, path, payload))
        if path == "/runtime":
            return {
                "gateway": {
                    "enabled": True,
                    "url_configured": True,
                    "mode": "rabbitmq",
                    "default_handoff_status": "available",
                    "target_kind": "local_mock",
                    "runtime_config_blockers": [],
                }
            }
        raise AssertionError("live-stack acceptance should stop before drafting a strategy")

    monkeypatch.setattr(live_acceptance.ApiClient, "call", fake_call)

    with pytest.raises(AssertionError, match="gateway mode=http"):
        live_acceptance.run_acceptance(
            base_url="http://127.0.0.1:8802",
            mock_gateway_health_url="http://127.0.0.1:5621/health",
            timeout=1,
            symbol="BTC",
            confirm_local_mock_handoff=True,
        )

    assert calls == [("GET", "/runtime", None)]


def test_live_stack_acceptance_api_client_http_error_is_sanitized(monkeypatch):
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
        client.call("POST", "/runtime", {"x": 1})

    message = str(exc_info.value)
    assert "POST /runtime -> HTTP 503" in message
    _assert_no_secret_echo(message)


def test_live_stack_acceptance_main_failure_report_is_sanitized(monkeypatch, capsys):
    def failing_run_acceptance(**kwargs):
        raise RuntimeError(
            "api_key=secret Bearer token=secret private_key=secret https://auth.internal"
        )

    monkeypatch.setattr(live_acceptance, "run_acceptance", failing_run_acceptance)
    monkeypatch.setattr(sys, "argv", ["ai_trading_v1_live_stack_acceptance.py", "--confirm-local-mock-handoff"])

    assert live_acceptance.main() == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "success": False,
        "error": live_acceptance.SAFE_ACCEPTANCE_ERROR_MESSAGE,
        "error_type": "RuntimeError",
    }
    _assert_no_secret_echo(payload)
