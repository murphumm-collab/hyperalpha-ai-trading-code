import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_v1_completion_audit.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_completion_audit", SCRIPT_PATH)
completion_audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = completion_audit
SPEC.loader.exec_module(completion_audit)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_minimal_acceptance_repo(root: Path, *, include_db_gate: bool = True, include_external_markers: bool = True) -> None:
    db_gate_text = (
        "Default production readiness DB-audit gate remains blocked\n"
        "--include-db-audits\n"
    ) if include_db_gate else ""
    _write(
        root / "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh",
        "\n".join(
            [
                "--confirm-local-mock-handoff",
                db_gate_text,
                "Frontend build",
                "ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff",
            ]
        ),
    )

    external_markers = "\n".join(
        [
            "实际 macOS 整机重启后的自动恢复还未物理验收",
            "真实 DeepSeek/Qwen API key live model-adjust 未验收",
            "真实 HyperAlpha 订单后端 URL/token live handoff 未验收",
            "真实 HTTPS 订单后端 URL/token、真实 Auth/JWKS、硬风控生产值",
            "真实登录态/真实 Auth 配置下的可视化验收未做",
            "真实生产登录态下的 session 详情页验收另行处理",
            "真实交易所执行不属于 V1 本地验收完成条件",
        ]
    ) if include_external_markers else ""
    _write(
        root / "docs/hyperalpha/ai-trading-v1-acceptance-checklist.zh-CN.md",
        "\n".join(
            [
                "一键本地 V1 验收通过",
                "默认生产 DB-audit readiness gate 阻断",
                "当前未验收",
                "最新证据为 spec `#41`、signal event `#39`、agent_sessions.total=26、handoff_attempts.total=37",
                external_markers,
            ]
        ),
    )
    _write(
        root / "docs/hyperalpha/status/ai-agent-multitenant-foundation.status.md",
        "\n".join(
            [
                "Local V1 Completion Boundary Audit Accepted / Remote Push Skipped",
                "| AI Trading aggregate acceptance DB-audit gate | Done |",
                "| AI Trading V1 completion boundary audit | Done |",
                "| Remote push | Deferred | GitHub upload intentionally skipped per user request |",
            ]
        ),
    )
    _write(
        root / "docs/hyperalpha/ai-trading-signal-gateway-contract.md",
        "\n".join(
            [
                "AI Trading emits reviewed trade signals only",
                "AI agent and AI Trading API must not place exchange orders directly",
                "order_backend_only",
                "not_an_order=true",
                "ai_may_place_orders=false",
                "requires_user_confirmation=true",
                "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
            ]
        ),
    )
    _write(
        root / "docs/hyperalpha/development-governance.zh-CN.md",
        "\n".join(
            [
                "先做上下文记忆压缩，再开发",
                "测试未通过不能验收",
                "未验收不能标记完成",
                "GitHub 上传必须走分支管理，不直接合并",
                "implemented != done",
                "accepted 才能进入完成清单",
            ]
        ),
    )
    _write(
        root / "docs/hyperalpha/memory/latest.md",
        "Current: `2026-06-10-ai-trading-production-readiness-cli-db-audits.zh-CN.md`",
    )
    _write(
        root / "docs/hyperalpha/memory/2026-06-10-ai-trading-production-readiness-cli-db-audits.zh-CN.md",
        "\n".join(
            [
                "GitHub 上传：按用户要求跳过",
                "default production readiness DB-audit blocker",
                "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
                "真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key",
            ]
        ),
    )


def test_current_repo_completion_audit_accepts_local_v1_but_not_live_orders():
    repo_root = Path(__file__).resolve().parents[2]

    report = completion_audit.build_completion_report(repo_root)

    assert report["local_v1_accepted"] is True
    assert report["ready_for_live_orders"] is False
    assert report["github_upload"] == "deferred_by_user_request"
    assert report["summary"]["local_track"] == "accepted"
    assert report["summary"]["production_track"] == "pending_external_acceptance"
    assert report["summary"]["local_blockers"] == []
    assert report["summary"]["missing_external_markers"] == []
    assert report["summary"]["external_pending_count"] >= 6
    statuses = {item["id"]: item["status"] for item in report["external_acceptance"]}
    assert statuses["real_order_backend_handoff"] == "pending_external_acceptance"
    assert statuses["real_exchange_execution"] == "out_of_local_v1_scope"


def test_completion_audit_blocks_local_acceptance_when_db_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_db_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Default production readiness DB-audit gate remains blocked" in runner_evidence["missing_phrases"]
    assert "--include-db-audits" in runner_evidence["missing_phrases"]


def test_completion_audit_requires_external_pending_markers(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_external_markers=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "real_model_profile_live_acceptance" in report["summary"]["missing_external_markers"]
    assert "real_order_backend_handoff" in report["summary"]["missing_external_markers"]
