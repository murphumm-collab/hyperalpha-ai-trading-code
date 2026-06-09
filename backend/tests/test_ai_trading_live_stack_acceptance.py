import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_v1_live_stack_acceptance.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_live_stack_acceptance", SCRIPT_PATH)
live_acceptance = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = live_acceptance
SPEC.loader.exec_module(live_acceptance)


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
