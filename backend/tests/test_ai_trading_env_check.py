import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_v1_env_check.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_env_check", SCRIPT_PATH)
env_check = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = env_check
SPEC.loader.exec_module(env_check)


def _patch_ready_dependencies(
    monkeypatch,
    *,
    runtime_gateway,
    runtime_model_adjustment=None,
    runtime_agent_context_budget=None,
):
    monkeypatch.setattr(env_check, "_docker_ready", lambda: {"installed": True, "daemon_ready": True})
    monkeypatch.setattr(env_check, "_tcp_open", lambda host, port, timeout=1.0: True)
    runtime_model_adjustment = runtime_model_adjustment or {
        "ready": False,
        "configured": False,
        "provider": None,
        "model": None,
        "provider_supported": False,
        "blockers": ["model_profile_not_configured"],
        "credential_present": False,
        "credential_value_returned": False,
    }
    if runtime_agent_context_budget is None:
        runtime_agent_context_budget = {
            "total": 1,
            "active": 1,
            "archived": 0,
            "with_context_summary": 0,
            "empty_context_summary": 1,
            "context_summary_max_chars": 2000,
            "near_budget_threshold_chars": 1800,
            "max_context_summary_chars": 0,
            "near_budget_count": 0,
            "over_budget_count": 0,
            "redacted_context_summary_count": 0,
            "sensitive_context_summary_count": 0,
            "secret_policy": "counts_only_no_summary_text",
        }

    def fake_http_probe(url, timeout=3.0):
        if url.endswith("/api/ai-trading/runtime"):
            return {
                "ok": True,
                "status": 200,
                "body_sample": "{}",
                "json": {
                    "gateway": runtime_gateway,
                    "model_adjustment": runtime_model_adjustment,
                    "agent_sessions": {"total": 1, "context_budget": runtime_agent_context_budget},
                },
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
    assert report["checks"]["backend_8802"]["runtime_model_adjustment"]["ready"] is False
    assert (
        report["checks"]["backend_8802"]["runtime_agent_context_budget"]["secret_policy"]
        == "counts_only_no_summary_text"
    )
    assert (
        report["checks"]["backend_8802"]["runtime_model_adjustment"]["blockers"]
        == ["model_profile_not_configured"]
    )
    assert report["next_actions"] == [
        "Local AI Trading V1 runtime is ready; continue with browser acceptance or the aggregate V1 local acceptance runner."
    ]


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
    assert report["next_actions"] == [
        "Point local backend AI_TRADING_SIGNAL_GATEWAY_URL at the local mock gateway before V1 local acceptance."
    ]


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
    assert report["next_actions"] == [
        "Clear backend runtime gateway blockers before submitting a local mock handoff acceptance."
    ]


def test_env_check_blocks_missing_agent_context_budget(monkeypatch):
    _patch_ready_dependencies(
        monkeypatch,
        runtime_gateway={
            "enabled": True,
            "url_configured": True,
            "target_kind": "local_mock",
            "runtime_config_blockers": [],
        },
        runtime_agent_context_budget={},
    )

    report = env_check.build_report(
        frontend_url="http://127.0.0.1:5174/app/ai-trading",
        backend_url="http://127.0.0.1:8802",
        mock_gateway_url="http://127.0.0.1:5621",
    )

    assert report["ready"] is False
    assert "backend_agent_context_budget_missing" in report["blockers"]
    assert report["next_actions"] == [
        "Restart/sync the backend so `/api/ai-trading/runtime` returns counts-only `agent_sessions.context_budget`."
    ]


def test_env_check_blocks_agent_context_budget_secret_policy_regression(monkeypatch):
    _patch_ready_dependencies(
        monkeypatch,
        runtime_gateway={
            "enabled": True,
            "url_configured": True,
            "target_kind": "local_mock",
            "runtime_config_blockers": [],
        },
        runtime_agent_context_budget={
            "total": 1,
            "active": 1,
            "archived": 0,
            "secret_policy": "raw_summary_text_returned",
        },
    )

    report = env_check.build_report(
        frontend_url="http://127.0.0.1:5174/app/ai-trading",
        backend_url="http://127.0.0.1:8802",
        mock_gateway_url="http://127.0.0.1:5621",
    )

    assert report["ready"] is False
    assert "backend_agent_context_budget_secret_policy_invalid" in report["blockers"]
    assert report["next_actions"] == [
        "Keep runtime agent-session context budget counts-only and do not return raw summary text."
    ]


def test_env_check_next_actions_match_missing_dependencies(monkeypatch):
    monkeypatch.setattr(env_check, "_docker_ready", lambda: {"installed": True, "daemon_ready": False})

    def fake_tcp_open(host, port, timeout=1.0):
        return False

    def fake_http_probe(url, timeout=3.0):
        return {"ok": False, "status": 503, "body_sample": ""}

    monkeypatch.setattr(env_check, "_tcp_open", fake_tcp_open)
    monkeypatch.setattr(env_check, "_http_probe", fake_http_probe)

    report = env_check.build_report(
        frontend_url="http://127.0.0.1:5174/app/ai-trading",
        backend_url="http://127.0.0.1:8802",
        mock_gateway_url="http://127.0.0.1:5621",
    )

    assert report["ready"] is False
    assert report["blockers"] == [
        "frontend_ai_trading_page_unreachable",
        "postgres_5432_not_listening",
        "docker_daemon_not_ready",
        "backend_ai_trading_runtime_unreachable",
        "mock_signal_gateway_unreachable",
    ]
    assert report["next_actions"] == [
        "Start Docker Desktop/daemon, then run `docker compose up -d postgres` from repo root.",
        "Start mock gateway: `cd backend && uv run uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1`.",
        "Start backend with AI_TRADING_SIGNAL_GATEWAY_URL pointing at the mock gateway.",
        "Start the frontend and open `/app/ai-trading` for browser acceptance.",
    ]
