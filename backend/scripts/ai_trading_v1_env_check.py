"""Check local environment readiness for AI Trading V1 browser acceptance.

This script does not start or stop services. It only probes expected local
dependencies and prints a JSON report.

Run from backend:

    uv run python scripts/ai_trading_v1_env_check.py

Use --strict to exit non-zero when any required component is missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_ROOT = Path.home() / "Library/Application Support/HyperAlpha/runtime/hyperalpha-ai-trading"
RUNTIME_SYNC_METADATA_FILE = ".hyperalpha-runtime-sync.json"


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


def _tracked_tree_digest(repo_root: Path) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except Exception as exc:
        return {
            "available": False,
            "error": exc.__class__.__name__,
            "message": str(exc)[:200],
        }

    paths = [
        raw_path.decode("utf-8", errors="surrogateescape")
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    ]
    digest = hashlib.sha256()
    file_count = 0
    for relative_path in sorted(paths):
        path = repo_root / relative_path
        if not path.is_file():
            continue
        digest.update(relative_path.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        file_count += 1
    return {
        "available": True,
        "digest": digest.hexdigest(),
        "tracked_file_count": file_count,
    }


def _runtime_mirror_report(repo_root: str | Path, runtime_root: str | Path) -> Dict[str, Any]:
    repo = Path(repo_root).expanduser().resolve()
    runtime = Path(runtime_root).expanduser().resolve()
    metadata_path = runtime / RUNTIME_SYNC_METADATA_FILE
    source_digest = _tracked_tree_digest(repo)
    blockers: List[str] = []
    metadata: Dict[str, Any] = {}

    if not metadata_path.exists():
        blockers.append("runtime_mirror_metadata_missing")
    else:
        try:
            parsed = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blockers.append("runtime_mirror_metadata_invalid_json")
        else:
            metadata = parsed if isinstance(parsed, dict) else {}
            if metadata.get("version") != "hyperalpha.local_runtime_sync.v1":
                blockers.append("runtime_mirror_metadata_version_invalid")
            if not metadata.get("source_tree_digest"):
                blockers.append("runtime_mirror_source_tree_digest_missing")

    if not source_digest.get("available"):
        blockers.append("runtime_mirror_source_digest_unavailable")
    elif metadata and metadata.get("source_tree_digest") != source_digest.get("digest"):
        blockers.append("runtime_mirror_source_tree_digest_mismatch")

    return {
        "current": not blockers,
        "blockers": blockers,
        "repo_root": str(repo),
        "runtime_root": str(runtime),
        "metadata_path": str(metadata_path),
        "metadata_present": metadata_path.exists(),
        "source_tree_digest": source_digest,
        "metadata": {
            "version": metadata.get("version"),
            "source_git_branch": metadata.get("source_git_branch"),
            "source_git_commit": metadata.get("source_git_commit"),
            "source_tree_digest": metadata.get("source_tree_digest"),
            "synced_at": metadata.get("synced_at"),
        } if metadata else {},
        "secret_policy": "metadata_only_no_env_or_credentials",
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
    if "backend_agent_context_budget_missing" in blocker_set:
        actions.append(
            "Restart/sync the backend so `/api/ai-trading/runtime` returns counts-only `agent_sessions.context_budget`."
        )
    if "backend_agent_context_budget_secret_policy_invalid" in blocker_set:
        actions.append("Keep runtime agent-session context budget counts-only and do not return raw summary text.")
    if "runtime_mirror_metadata_missing" in blocker_set or "runtime_mirror_source_tree_digest_mismatch" in blocker_set:
        actions.append("Run `scripts/local-dev/install_launch_agent.sh` to sync the LaunchAgent runtime mirror to the current source tree.")
    if "runtime_mirror_metadata_invalid_json" in blocker_set or "runtime_mirror_metadata_version_invalid" in blocker_set:
        actions.append("Reinstall the local LaunchAgent runtime mirror so sync metadata is regenerated.")
    if "runtime_mirror_source_digest_unavailable" in blocker_set:
        actions.append("Run env-check from a valid Git worktree so the local runtime mirror can be compared safely.")
    if "frontend_ai_trading_page_unreachable" in blocker_set:
        actions.append("Start the frontend and open `/app/ai-trading` for browser acceptance.")
    if not actions:
        actions.append(
            "Local AI Trading V1 runtime is ready; continue with browser acceptance or the aggregate V1 local acceptance runner."
        )
    return actions


def build_report(
    frontend_url: str,
    backend_url: str,
    mock_gateway_url: str,
    *,
    repo_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
    require_runtime_mirror_current: bool = False,
) -> Dict[str, Any]:
    docker = _docker_ready()
    postgres_open = _tcp_open("127.0.0.1", 5432)
    docker_required_for_readiness = not postgres_open
    if postgres_open and not docker.get("daemon_ready"):
        docker["readiness_blocker_suppressed"] = "postgres_5432_already_listening"
    docker["required_for_readiness"] = docker_required_for_readiness
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
    runtime_agent_sessions = (
        runtime_payload.get("agent_sessions")
        if isinstance(runtime_payload.get("agent_sessions"), dict)
        else {}
    )
    runtime_agent_context_budget = (
        runtime_agent_sessions.get("context_budget")
        if isinstance(runtime_agent_sessions.get("context_budget"), dict)
        else {}
    )
    runtime_mirror = (
        _runtime_mirror_report(repo_root, runtime_root)
        if repo_root is not None and runtime_root is not None
        else {}
    )

    blockers: List[str] = []
    if not frontend.get("ok"):
        blockers.append("frontend_ai_trading_page_unreachable")
    if not postgres_open:
        blockers.append("postgres_5432_not_listening")
    if docker_required_for_readiness and not docker.get("daemon_ready"):
        blockers.append("docker_daemon_not_ready")
    if not backend_runtime.get("ok"):
        blockers.append("backend_ai_trading_runtime_unreachable")
    else:
        if runtime_gateway.get("target_kind") != "local_mock":
            blockers.append("backend_gateway_target_not_local_mock")
        if runtime_gateway.get("runtime_config_blockers"):
            blockers.append("backend_gateway_runtime_config_blocked")
        if not runtime_agent_context_budget:
            blockers.append("backend_agent_context_budget_missing")
        elif runtime_agent_context_budget.get("secret_policy") != "counts_only_no_summary_text":
            blockers.append("backend_agent_context_budget_secret_policy_invalid")
    if require_runtime_mirror_current and runtime_mirror and not runtime_mirror.get("current"):
        blockers.extend(runtime_mirror.get("blockers") or ["runtime_mirror_not_current"])
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
                "runtime_agent_context_budget": runtime_agent_context_budget,
            },
            "mock_gateway_5621": {"tcp_open": mock_gateway_open, "health": mock_gateway},
            "runtime_mirror": runtime_mirror,
        },
        "next_actions": _next_actions_for_blockers(blockers),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5174/app/ai-trading")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8802")
    parser.add_argument("--mock-gateway-url", default="http://127.0.0.1:5621")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument(
        "--require-runtime-mirror-current",
        action="store_true",
        help="Exit non-zero when the LaunchAgent runtime mirror metadata is missing or stale.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit 1 when any readiness blocker exists.")
    args = parser.parse_args()

    report = build_report(
        frontend_url=args.frontend_url,
        backend_url=args.backend_url,
        mock_gateway_url=args.mock_gateway_url,
        repo_root=args.repo_root,
        runtime_root=args.runtime_root,
        require_runtime_mirror_current=args.require_runtime_mirror_current,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
