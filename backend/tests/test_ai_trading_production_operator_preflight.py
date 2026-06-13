import importlib.util
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
PREFLIGHT_SCRIPT_PATH = SCRIPT_DIR / "ai_trading_v1_production_operator_preflight.py"
COMPLETION_SCRIPT_PATH = SCRIPT_DIR / "ai_trading_v1_completion_audit.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

COMPLETION_SPEC = importlib.util.spec_from_file_location("ai_trading_v1_completion_audit", COMPLETION_SCRIPT_PATH)
completion_audit = importlib.util.module_from_spec(COMPLETION_SPEC)
assert COMPLETION_SPEC.loader is not None
sys.modules[COMPLETION_SPEC.name] = completion_audit
COMPLETION_SPEC.loader.exec_module(completion_audit)

PREFLIGHT_SPEC = importlib.util.spec_from_file_location(
    "ai_trading_v1_production_operator_preflight",
    PREFLIGHT_SCRIPT_PATH,
)
operator_preflight = importlib.util.module_from_spec(PREFLIGHT_SPEC)
assert PREFLIGHT_SPEC.loader is not None
sys.modules[PREFLIGHT_SPEC.name] = operator_preflight
PREFLIGHT_SPEC.loader.exec_module(operator_preflight)

_TRANSIENT_RESOURCE_MARKERS = (
    "Resource temporarily unavailable",
    "Failed to spawn",
    "fork failed",
)


def _has_transient_resource_output(output: str) -> bool:
    return any(marker in output for marker in _TRANSIENT_RESOURCE_MARKERS)


def _run_subprocess_with_transient_retry(*popenargs, attempts: int = 3, **kwargs):
    last_result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(attempts):
        try:
            result = subprocess.run(*popenargs, **kwargs)
        except OSError as exc:
            if attempt < attempts - 1 and getattr(exc, "errno", None) == 35:
                time.sleep(1)
                continue
            raise

        last_result = result
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 0:
            return result
        if attempt < attempts - 1 and _has_transient_resource_output(output):
            time.sleep(1)
            continue
        return result
    assert last_result is not None
    return last_result


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_minimal_accepted_repo(root: Path) -> None:
    phrases_by_path: dict[str, list[str]] = defaultdict(list)
    for requirement in completion_audit.LOCAL_REQUIREMENTS + completion_audit.EXTERNAL_REQUIREMENTS:
        phrases_by_path[requirement.path].extend(requirement.required_phrases)

    phrases_by_path["docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md"].extend(
        [
            "spec `#144`",
            "signal event `#142`",
            "agent_sessions.total=129",
            "handoff_attempts.total=140",
        ]
    )
    for relative_path, phrases in phrases_by_path.items():
        _write(root / relative_path, "\n".join(dict.fromkeys(phrases)))

    acceptance_path = root / "docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md"
    acceptance_text = acceptance_path.read_text(encoding="utf-8")
    _write(
        acceptance_path,
        "\n".join(
            [
                acceptance_text,
                "Git：只在 `codex/ai-agent-multitenant-foundation` 分支开发；GitHub 上传已同步到 origin/codex/ai-agent-multitenant-foundation；不合并。",
            ]
        ),
    )
    status_path = root / "docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md"
    status_text = status_path.read_text(encoding="utf-8")
    _write(
        status_path,
        "\n".join(
            [
                "Branch: `codex/ai-agent-multitenant-foundation`",
                status_text,
                "| Remote push | Done | Branch pushed to origin/codex/ai-agent-multitenant-foundation; no merge performed |",
            ]
        ),
    )

    memory_file = "2026-06-12-ai-trading-production-operator-preflight.zh-CN.md"
    _write(root / "docs/hyperalpha/memory/latest.md", f"Current: `{memory_file}`")
    _write(
        root / "docs/hyperalpha/memory" / memory_file,
        "\n".join(
            [
                "GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation",
                completion_audit.EXPECTED_LOCAL_DEVELOPMENT_BRANCH,
                "已 push，不 merge",
                "default production readiness DB-audit blocker",
                "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
                "真实 Auth/JWKS、真实订单后端 URL/token、真实 Codex GPT-5.5 profile/API key",
            ]
        ),
    )
    _write(root / ".git/HEAD", f"ref: refs/heads/{completion_audit.EXPECTED_LOCAL_DEVELOPMENT_BRANCH}\n")


def test_operator_preflight_blocks_without_external_evidence_and_keeps_secrets_out(tmp_path):
    _write_minimal_accepted_repo(tmp_path)
    env_path = tmp_path / "production.env"
    _write(
        env_path,
        "\n".join(
            [
                "AUTH_REQUIRE_VERIFIED_BEARER=true",
                "AUTH_JWKS_URL=https://auth.hyperalpha.example/.well-known/jwks.json",
                "AUTH_JWT_ISSUER=https://auth.hyperalpha.example/",
                "AUTH_JWT_AUDIENCE=hyperalpha-prod",
                "AUTH_JWT_ALGORITHMS=RS256",
                "AUTH_ADMIN_USERNAMES=ops-admin",
                "AI_TRADING_SIGNAL_GATEWAY_ENABLED=true",
                "AI_TRADING_SIGNAL_GATEWAY_MODE=http",
                "AI_TRADING_SIGNAL_GATEWAY_URL=https://orders.hyperalpha.example/ai-trading/signals",
                "AI_TRADING_SIGNAL_GATEWAY_TOKEN=secret-production-token-123456789",
                "AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true",
                "AI_HARD_MAX_ORDER_NOTIONAL_USD=1000",
                "AI_HARD_REQUIRE_STOP_LOSS=true",
                "AI_HARD_REQUIRE_TAKE_PROFIT=true",
            ]
        ),
    )

    report = operator_preflight.build_operator_preflight_report(
        repo_root=tmp_path,
        env_file=str(env_path),
        skip_local_runtime=True,
    )
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)

    assert report["mode"] == "ai_trading_production_operator_preflight"
    assert report["preflight_ready"] is False
    assert report["ready_for_live_orders"] is False
    assert report["summary"]["local_v1_accepted"] is True
    assert report["summary"]["local_runtime_checked"] is False
    assert "completion:live_orders_not_ready" in report["blockers"]
    assert report["components"]["local_runtime"]["secret_policy"] == "skipped_no_probe"
    assert "secret-production-token-123456789" not in serialized
    assert "Authorization: Bearer" not in serialized
    assert completion_audit._secret_pattern_hits(report) == []


def test_operator_preflight_redacts_secret_like_external_evidence_paths(tmp_path):
    _write_minimal_accepted_repo(tmp_path)
    secret_path = tmp_path.parent / f"{tmp_path.name}-api_key=secret-production-token-123456789.json"

    report = operator_preflight.build_operator_preflight_report(
        repo_root=tmp_path,
        production_evidence_file=str(secret_path),
        skip_local_runtime=True,
    )
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
    production_evidence = report["components"]["completion"]["production_evidence"]

    assert production_evidence["provided"] is True
    assert production_evidence["path"] == operator_preflight.REDACTED_SENSITIVE_PREFLIGHT_VALUE
    assert "external_evidence_file_missing" in production_evidence["blockers"]
    assert "secret-production-token-123456789" not in serialized
    assert "api_key=" not in serialized
    assert completion_audit._secret_pattern_hits(report) == []


def test_operator_preflight_blocks_dirty_worktree_without_file_name_leakage(tmp_path, monkeypatch):
    _write_minimal_accepted_repo(tmp_path)

    def fake_run_git(repo_root, args):
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return completion_audit.EXPECTED_LOCAL_DEVELOPMENT_BRANCH
        if args == ["rev-parse", "HEAD"]:
            return "abc123def456abc123def456abc123def456abcd"
        if args == ["status", "--porcelain"]:
            return " M backend/secret-strategy.py\n?? .env.secret"
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(operator_preflight, "_run_git", fake_run_git)

    report = operator_preflight.build_operator_preflight_report(
        repo_root=tmp_path,
        skip_local_runtime=True,
    )
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
    git_report = report["components"]["git"]

    assert report["summary"]["git_branch_ready"] is False
    assert report["summary"]["git_dirty"] is True
    assert "git:working_tree_has_uncommitted_changes" in report["blockers"]
    assert "git:working_tree_has_uncommitted_changes" in report["warnings"]
    assert git_report["branch_ready"] is False
    assert git_report["dirty"] is True
    assert git_report["dirty_entry_count"] == 2
    assert git_report["blockers"] == ["working_tree_has_uncommitted_changes"]
    assert any("Commit or discard local source changes" in action for action in report["next_actions"])
    assert "backend/secret-strategy.py" not in serialized
    assert ".env.secret" not in serialized
    assert completion_audit._secret_pattern_hits(report) == []


def test_operator_preflight_cli_strict_exits_one_for_default_blockers(tmp_path):
    _write_minimal_accepted_repo(tmp_path)

    completed = _run_subprocess_with_transient_retry(
        [
            sys.executable,
            str(PREFLIGHT_SCRIPT_PATH),
            "--repo-root",
            str(tmp_path),
            "--skip-local-runtime",
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(PREFLIGHT_SCRIPT_PATH.parents[1]),
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert payload["mode"] == "ai_trading_production_operator_preflight"
    assert payload["preflight_ready"] is False
    assert payload["summary"]["github_upload"] == "pushed_to_origin"
    assert "completion:live_orders_not_ready" in payload["blockers"]
    assert "production_readiness:not_ready" in payload["blockers"]
    assert completion_audit._secret_pattern_hits(payload) == []
