"""Check local environment readiness for AI Trading V1 browser acceptance.

This script does not start or stop services. It only probes expected local
dependencies and prints a JSON report.

Run from backend:

    uv run python scripts/ai_trading_v1_env_check.py

Use --strict to exit non-zero when any required component is missing.
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _backend_port(backend_url: str) -> int:
    parsed = urllib.parse.urlparse(backend_url)
    if parsed.port:
        return int(parsed.port)
    return 443 if parsed.scheme == "https" else 80


def _http_probe(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        request = urllib.request.Request(url, method="GET", headers={"Accept": "*/*"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
            result: Dict[str, Any] = {
                "ok": 200 <= int(response.status) < 400,
                "status": int(response.status),
                "body_sample": body[:160],
            }
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                result["json"] = parsed
            return result
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": int(exc.code), "body_sample": exc.read(160).decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"ok": False, "error": exc.__class__.__name__, "message": str(exc)[:200]}


def _docker_ready() -> Dict[str, Any]:
    if not shutil.which("docker"):
        return {"installed": False, "daemon_ready": False}
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{json .Server.Version}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        return {
            "installed": True,
            "daemon_ready": False,
            "error": exc.__class__.__name__,
            "message": str(exc)[:200],
        }
    return {
        "installed": True,
        "daemon_ready": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip()[:300],
    }


def _next_actions_for_blockers(blockers: List[str]) -> List[str]:
    actions: List[str] = []
    blocker_set = set(blockers)
    if "docker_daemon_not_ready" in blocker_set or "postgres_5432_not_listening" in blocker_set:
        actions.append("Start Docker Desktop/daemon, then run `docker compose up -d postgres` from repo root.")
    if "mock_signal_gateway_unreachable" in blocker_set:
        actions.append(
            "Start mock gateway: `cd backend && uv run uvicorn dev_ai_trading_signal_gateway:app --port 5621 --host 127.0.0.1`."
        )
    if "backend_ai_trading_runtime_unreachable" in blocker_set:
        actions.append("Start backend with AI_TRADING_SIGNAL_GATEWAY_URL pointing at the mock gateway.")
    if "backend_gateway_target_not_local_mock" in blocker_set:
        actions.append(
            "Point local backend AI_TRADING_SIGNAL_GATEWAY_URL at the local mock gateway before V1 local acceptance."
        )
    if "backend_gateway_runtime_config_blocked" in blocker_set:
        actions.append("Clear backend runtime gateway blockers before submitting a local mock handoff acceptance.")
    if "frontend_ai_trading_page_unreachable" in blocker_set:
        actions.append("Start the frontend and open `/app/ai-trading` for browser acceptance.")
    if not actions:
        actions.append(
            "Local AI Trading V1 runtime is ready; continue with browser acceptance or the aggregate V1 local acceptance runner."
        )
    return actions


def build_report(frontend_url: str, backend_url: str, mock_gateway_url: str) -> Dict[str, Any]:
    docker = _docker_ready()
    postgres_open = _tcp_open("127.0.0.1", 5432)
    backend_port = _backend_port(backend_url)
    backend_open = _tcp_open("127.0.0.1", backend_port)
    mock_gateway_open = _tcp_open("127.0.0.1", 5621)

    frontend = _http_probe(frontend_url)
    backend_runtime = _http_probe(f"{backend_url.rstrip('/')}/api/ai-trading/runtime", timeout=45.0) if backend_open else {
        "ok": False,
        "message": f"backend port {backend_port} is not listening",
    }
    mock_gateway = _http_probe(f"{mock_gateway_url.rstrip('/')}/health") if mock_gateway_open else {
        "ok": False,
        "message": "mock gateway port 5621 is not listening",
    }
    runtime_payload = backend_runtime.get("json") if isinstance(backend_runtime.get("json"), dict) else {}
    runtime_gateway = runtime_payload.get("gateway") if isinstance(runtime_payload.get("gateway"), dict) else {}
    runtime_model_adjustment = (
        runtime_payload.get("model_adjustment")
        if isinstance(runtime_payload.get("model_adjustment"), dict)
        else {}
    )

    blockers: List[str] = []
    if not frontend.get("ok"):
        blockers.append("frontend_ai_trading_page_unreachable")
    if not postgres_open:
        blockers.append("postgres_5432_not_listening")
    if not docker.get("daemon_ready"):
        blockers.append("docker_daemon_not_ready")
    if not backend_runtime.get("ok"):
        blockers.append("backend_ai_trading_runtime_unreachable")
    else:
        if runtime_gateway.get("target_kind") != "local_mock":
            blockers.append("backend_gateway_target_not_local_mock")
        if runtime_gateway.get("runtime_config_blockers"):
            blockers.append("backend_gateway_runtime_config_blocked")
    if not mock_gateway.get("ok"):
        blockers.append("mock_signal_gateway_unreachable")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "expected_acceptance_urls": {
            "frontend": frontend_url,
            "backend_runtime": f"{backend_url.rstrip('/')}/api/ai-trading/runtime",
            "mock_gateway_health": f"{mock_gateway_url.rstrip('/')}/health",
        },
        "checks": {
            "docker": docker,
            "postgres_5432": {"tcp_open": postgres_open},
            "frontend": frontend,
            f"backend_{backend_port}": {
                "tcp_open": backend_open,
                "runtime": backend_runtime,
                "runtime_gateway": runtime_gateway,
                "runtime_model_adjustment": runtime_model_adjustment,
            },
            "mock_gateway_5621": {"tcp_open": mock_gateway_open, "health": mock_gateway},
        },
        "next_actions": _next_actions_for_blockers(blockers),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5174/app/ai-trading")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8802")
    parser.add_argument("--mock-gateway-url", default="http://127.0.0.1:5621")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when any readiness blocker exists.")
    args = parser.parse_args()

    report = build_report(
        frontend_url=args.frontend_url,
        backend_url=args.backend_url,
        mock_gateway_url=args.mock_gateway_url,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
