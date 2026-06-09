import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_v1_env_check.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_env_check", SCRIPT_PATH)
env_check = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = env_check
SPEC.loader.exec_module(env_check)


def _patch_ready_dependencies(monkeypatch, *, runtime_gateway):
    monkeypatch.setattr(env_check, "_docker_ready", lambda: {"installed": True, "daemon_ready": True})
    monkeypatch.setattr(env_check, "_tcp_open", lambda host, port, timeout=1.0: True)

    def fake_http_probe(url, timeout=3.0):
        if url.endswith("/api/ai-trading/runtime"):
            return {
                "ok": True,
                "status": 200,
                "body_sample": "{}",
                "json": {"gateway": runtime_gateway},
            }
        if url.endswith("/health"):
            return {
                "ok": True,
                "status": 200,
                "body_sample": "{}",
                "json": {"ok": True, "service": "ai_trading_mock_signal_gateway"},
            }
        return {"ok": True, "status": 200, "body_sample": "<html></html>"}

    monkeypatch.setattr(env_check, "_http_probe", fake_http_probe)


def test_env_check_ready_requires_local_mock_gateway(monkeypatch):
    _patch_ready_dependencies(
        monkeypatch,
        runtime_gateway={
            "enabled": True,
            "url_configured": True,
            "target_kind": "local_mock",
            "runtime_config_blockers": [],
        },
    )

    report = env_check.build_report(
        frontend_url="http://127.0.0.1:5174/app/ai-trading",
        backend_url="http://127.0.0.1:8802",
        mock_gateway_url="http://127.0.0.1:5621",
    )

    assert report["ready"] is True
    assert report["blockers"] == []
    assert report["checks"]["backend_8802"]["runtime_gateway"]["target_kind"] == "local_mock"


def test_env_check_blocks_external_runtime_gateway(monkeypatch):
    _patch_ready_dependencies(
        monkeypatch,
        runtime_gateway={
            "enabled": True,
            "url_configured": True,
            "target_kind": "external_order_backend",
            "runtime_config_blockers": [],
        },
    )

    report = env_check.build_report(
        frontend_url="http://127.0.0.1:5174/app/ai-trading",
        backend_url="http://127.0.0.1:8802",
        mock_gateway_url="http://127.0.0.1:5621",
    )

    assert report["ready"] is False
    assert "backend_gateway_target_not_local_mock" in report["blockers"]


def test_env_check_blocks_runtime_gateway_config_blockers(monkeypatch):
    _patch_ready_dependencies(
        monkeypatch,
        runtime_gateway={
            "enabled": True,
            "url_configured": True,
            "target_kind": "local_mock",
            "runtime_config_blockers": ["production_handoff_approval_required"],
        },
    )

    report = env_check.build_report(
        frontend_url="http://127.0.0.1:5174/app/ai-trading",
        backend_url="http://127.0.0.1:8802",
        mock_gateway_url="http://127.0.0.1:5621",
    )

    assert report["ready"] is False
    assert "backend_gateway_runtime_config_blocked" in report["blockers"]
