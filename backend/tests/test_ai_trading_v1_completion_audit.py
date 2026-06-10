import importlib.util
import json
import subprocess
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


def _write_minimal_acceptance_repo(
    root: Path,
    *,
    include_db_gate: bool = True,
    include_frontend_source_guard: bool = True,
    include_production_evidence_explain_gate: bool = True,
    include_admin_production_evidence_explain_api_marker: bool = True,
    include_admin_production_evidence_ui_marker: bool = True,
    include_admin_production_evidence_validation_api_marker: bool = True,
    include_admin_production_evidence_validation_ui_marker: bool = True,
    include_admin_production_evidence_template_api_marker: bool = True,
    include_admin_production_evidence_template_ui_marker: bool = True,
    include_admin_production_evidence_payload_bounds_marker: bool = True,
    include_agent_session_response_context_redaction_marker: bool = True,
    include_frontend_session_context_prompt_sanitizer_marker: bool = True,
    include_model_adjust_untrusted_context_boundary_marker: bool = True,
    include_model_adjust_output_sanitizer_marker: bool = True,
    include_frontend_model_adjust_output_safety_marker: bool = True,
    include_frontend_validation_warning_labels_marker: bool = True,
    include_external_markers: bool = True,
    git_branch: str = "codex/ai-agent-multitenant-foundation",
) -> None:
    db_gate_text = (
        "Default production readiness DB-audit gate remains blocked\n"
        "--include-db-audits\n"
    ) if include_db_gate else ""
    frontend_source_guard_text = (
        "tests/test_ai_trading_frontend_readiness_source.py\n"
    ) if include_frontend_source_guard else ""
    explain_gate_text = (
        "Production evidence explain mode gate\n"
        "--explain-production-evidence\n"
        "production_evidence_explain_gate\n"
    ) if include_production_evidence_explain_gate else ""
    admin_explain_api_marker = (
        "| AI Trading admin production evidence explain API | Done |"
    ) if include_admin_production_evidence_explain_api_marker else ""
    admin_evidence_ui_marker = (
        "| AI Trading admin production evidence UI | Done |"
    ) if include_admin_production_evidence_ui_marker else ""
    admin_validation_api_marker = (
        "| AI Trading admin production evidence validation API | Done |"
    ) if include_admin_production_evidence_validation_api_marker else ""
    admin_validation_ui_marker = (
        "| AI Trading admin production evidence validation UI | Done |"
    ) if include_admin_production_evidence_validation_ui_marker else ""
    admin_template_api_marker = (
        "| AI Trading admin production evidence template API | Done |"
    ) if include_admin_production_evidence_template_api_marker else ""
    admin_template_ui_marker = (
        "| AI Trading admin production evidence template UI | Done |"
    ) if include_admin_production_evidence_template_ui_marker else ""
    admin_payload_bounds_marker = (
        "| AI Trading admin production evidence payload bounds | Done |"
    ) if include_admin_production_evidence_payload_bounds_marker else ""
    agent_session_response_context_redaction_marker = (
        "| AI Trading agent-session response context redaction | Done |"
    ) if include_agent_session_response_context_redaction_marker else ""
    frontend_session_context_prompt_sanitizer_marker = (
        "| AI Trading frontend session context prompt sanitizer | Done |"
    ) if include_frontend_session_context_prompt_sanitizer_marker else ""
    model_adjust_untrusted_context_boundary_marker = (
        "| AI Trading model-adjust untrusted context boundary | Done |"
    ) if include_model_adjust_untrusted_context_boundary_marker else ""
    model_adjust_output_sanitizer_marker = (
        "| AI Trading model-adjust output sanitizer | Done |"
    ) if include_model_adjust_output_sanitizer_marker else ""
    frontend_model_adjust_output_safety_marker = (
        "| AI Trading frontend model-adjust output safety | Done |"
    ) if include_frontend_model_adjust_output_safety_marker else ""
    frontend_validation_warning_labels_marker = (
        "| AI Trading frontend validation warning labels | Done |"
    ) if include_frontend_validation_warning_labels_marker else ""
    _write(
        root / "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh",
        "\n".join(
            [
                "--confirm-local-mock-handoff",
                db_gate_text,
                frontend_source_guard_text,
                "Frontend build",
                "local completion summary gate",
                "git_governance.status",
                "ready_for_live_orders_false",
                "deferred_by_user_request",
                "codex/ai-agent-multitenant-foundation",
                "ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff",
                "Production evidence template remains blocked",
                explain_gate_text,
                "Production evidence initializer gate",
                "--init-production-evidence-file",
                "production_evidence_initializer_gate",
                "real_order_backend_blocked",
                "Local LaunchAgent runtime sync",
                "scripts/local-dev/install_launch_agent.sh",
                "--require-runtime-mirror-current",
                "Runtime readiness attempt",
                "run_runtime_readiness_with_retry",
                "--production-evidence-file ../docs/hyperalpha/ai-trading-v1-production-evidence.template.json --strict-production",
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
                "Git：只在 `codex/ai-agent-multitenant-foundation` 分支本地提交；GitHub 上传按当前用户要求暂不处理。",
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
                "Branch: `codex/ai-agent-multitenant-foundation`",
                "Local V1 Frontend Validation Warning Labels Accepted / Remote Push Skipped",
                "| AI Trading aggregate acceptance DB-audit gate | Done |",
                "| AI Trading V1 completion boundary audit | Done |",
                "| AI Trading production evidence gate | Done |",
                "| AI Trading production evidence text quality | Done |",
                "| AI Trading production evidence text bounds | Done |",
                "| AI Trading production evidence artifact-ref bounds | Done |",
                "| AI Trading production evidence item IDs | Done |",
                "| AI Trading production evidence path safety | Done |",
                "| AI Trading production evidence note safety | Done |",
                "| AI Trading production evidence initializer | Done |",
                "| AI Trading aggregate production evidence initializer gate | Done |",
                "| AI Trading production evidence explain mode | Done |",
                "| AI Trading aggregate production evidence explain gate | Done |",
                admin_explain_api_marker,
                admin_evidence_ui_marker,
                admin_validation_api_marker,
                admin_validation_ui_marker,
                admin_template_api_marker,
                admin_template_ui_marker,
                admin_payload_bounds_marker,
                agent_session_response_context_redaction_marker,
                frontend_session_context_prompt_sanitizer_marker,
                model_adjust_untrusted_context_boundary_marker,
                model_adjust_output_sanitizer_marker,
                frontend_model_adjust_output_safety_marker,
                frontend_validation_warning_labels_marker,
                "| AI Trading runtime mirror freshness gate | Done |",
                "| AI Trading runtime readiness cold-start retry | Done |",
                "| AI Trading agent-session manual context secret rejection | Done |",
                "| AI Trading env-check runtime context budget gate | Done |",
                "| AI Trading runtime budget UI source guard | Done |",
                "| AI Trading completion audit git governance gate | Done |",
                "| AI Trading local completion summary gate | Done |",
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
                "codex/ai-agent-multitenant-foundation",
                "不 push、不 merge",
                "default production readiness DB-audit blocker",
                "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh --confirm-local-mock-handoff",
                "真实 Auth/JWKS、真实订单后端 URL/token、真实 DeepSeek/Qwen profile/API key",
            ]
        ),
    )
    _write(root / ".git/HEAD", f"ref: refs/heads/{git_branch}\n")


def _write_production_evidence(
    path: Path,
    *,
    include_secret: bool = False,
    missing_item: str | None = None,
    artifact_ref_override: str | None = None,
    empty_artifact_refs: bool = False,
    generated_at: object = "2026-06-10T12:05:00Z",
    validated_at: object = "2026-06-10T12:00:00Z",
    validated_by: object = "ops-admin",
    evidence_summary: object | None = None,
    root_extra: dict[str, object] | None = None,
    item_extra: dict[str, object] | None = None,
) -> None:
    items = {}
    for requirement in completion_audit.EXTERNAL_REQUIREMENTS:
        if requirement.id == missing_item:
            continue
        items[requirement.id] = {
            "status": "accepted",
            "validated_at": validated_at,
            "validated_by": validated_by,
            "evidence_summary": (
                evidence_summary
                if evidence_summary is not None
                else f"{requirement.id} accepted with sanitized operational evidence."
            ),
            "artifact_refs": (
                []
                if empty_artifact_refs
                else [artifact_ref_override or f"ops://ai-trading/{requirement.id}/acceptance"]
            ),
            "secret_values_returned": False,
        }
        if item_extra:
            items[requirement.id].update(item_extra)
    payload = {
        "version": completion_audit.EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "generated_at": generated_at,
        "secret_values_returned": False,
        "items": items,
    }
    if root_extra:
        payload.update(root_extra)
    if include_secret:
        payload["items"]["real_order_backend_handoff"]["evidence_summary"] = (
            "accepted with "
            + "Authorization: "
            + "Bearer "
            + "secret-production-"
            + "token-123456789"
        )
    _write(path, json.dumps(payload, indent=2, sort_keys=True))


def _outside_repo_evidence_path(repo_root: Path, filename: str) -> Path:
    return repo_root.parent / f"{repo_root.name}-{filename}"


def test_current_repo_completion_audit_accepts_local_v1_but_not_live_orders():
    repo_root = Path(__file__).resolve().parents[2]

    report = completion_audit.build_completion_report(repo_root)

    assert report["local_v1_accepted"] is True
    assert report["ready_for_live_orders"] is False
    assert report["github_upload"] == "deferred_by_user_request"
    assert report["git_governance"]["status"] == "accepted"
    assert report["git_governance"]["current_branch"] == "codex/ai-agent-multitenant-foundation"
    assert report["summary"]["local_track"] == "accepted"
    assert report["summary"]["production_track"] == "pending_external_acceptance"
    assert report["summary"]["local_blockers"] == []
    assert report["summary"]["missing_external_markers"] == []
    assert report["summary"]["external_pending_count"] >= 6
    assert report["summary"]["documented_external_pending_count"] == report["summary"]["external_pending_count"]
    assert report["production_evidence"]["provided"] is False
    assert report["production_evidence"]["ready"] is False
    statuses = {item["id"]: item["status"] for item in report["external_acceptance"]}
    assert statuses["real_order_backend_handoff"] == "pending_external_acceptance"
    assert statuses["real_exchange_execution"] == "out_of_local_v1_scope"


def test_production_evidence_template_builder_uses_required_item_ids_without_secrets():
    payload = completion_audit.build_external_acceptance_evidence_template()

    assert payload["version"] == completion_audit.EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION
    assert payload["generated_at"] is None
    assert payload["secret_values_returned"] is False
    assert set(payload["items"]) == {requirement.id for requirement in completion_audit.EXTERNAL_REQUIREMENTS}
    assert all(item["status"] == "pending_external_acceptance" for item in payload["items"].values())
    assert all(item["secret_values_returned"] is False for item in payload["items"].values())
    assert completion_audit._secret_pattern_hits(payload) == []


def test_production_evidence_explain_reports_item_level_missing_evidence(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)

    report = completion_audit.build_production_evidence_explain(tmp_path)

    assert report["mode"] == "production_evidence_explain"
    assert report["local_v1_accepted"] is True
    assert report["ready_for_live_orders"] is False
    assert report["production_evidence"]["provided"] is False
    assert report["schema"]["required_item_ids"] == [
        requirement.id for requirement in completion_audit.EXTERNAL_REQUIREMENTS
    ]
    assert "status=accepted" in report["schema"]["required_item_fields"]
    order_backend_item = next(
        item for item in report["items"] if item["id"] == "real_order_backend_handoff"
    )
    assert order_backend_item["ready"] is False
    assert "external_evidence_item_not_provided" in order_backend_item["blockers"]
    assert "API keys" in order_backend_item["forbidden_values"]
    assert "Configure the real HTTPS order-backend signal gateway" in order_backend_item["operator_guidance"][0]


def test_production_evidence_explain_keeps_live_orders_blocked_without_explicit_confirmation(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    evidence_path = _outside_repo_evidence_path(tmp_path, "production-evidence.json")
    _write_production_evidence(evidence_path)

    report = completion_audit.build_production_evidence_explain(
        tmp_path,
        production_evidence_file=evidence_path,
    )

    assert report["production_evidence"]["ready"] is True
    assert report["production_evidence"]["accepted_count"] == len(completion_audit.EXTERNAL_REQUIREMENTS)
    assert report["production_track"] == "external_evidence_accepted_pending_explicit_confirmation"
    assert report["ready_for_live_orders"] is False
    assert all(item["ready"] is True for item in report["items"])
    assert all(item["blockers"] == [] for item in report["items"])


def test_production_evidence_explain_cli_outputs_non_secret_checklist(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--repo-root",
            str(tmp_path),
            "--explain-production-evidence",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["mode"] == "production_evidence_explain"
    assert payload["github_upload"] == "deferred_by_user_request"
    assert payload["production_evidence"]["ready"] is False
    assert "bearer tokens" in payload["items"][0]["forbidden_values"]
    assert completion_audit._secret_pattern_hits(payload) == []


def test_production_evidence_initializer_writes_repo_external_pending_template(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    output_path = _outside_repo_evidence_path(tmp_path, "initialized-production-evidence.json")

    init_report = completion_audit.write_external_acceptance_evidence_template(
        output_path,
        repo_root=tmp_path,
    )
    completion_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=output_path,
        allow_live_ready_from_evidence=True,
    )

    assert init_report["created"] is True
    assert init_report["ready_for_live_orders"] is False
    assert init_report["production_evidence_ready"] is False
    assert output_path.exists()
    assert completion_report["local_v1_accepted"] is True
    assert completion_report["ready_for_live_orders"] is False
    assert completion_report["production_evidence"]["provided"] is True
    assert completion_report["production_evidence"]["file_inside_repo"] is False
    assert completion_report["production_evidence"]["accepted_count"] == 0
    assert "external_evidence_generated_at_missing" in completion_report["production_evidence"]["blockers"]
    assert "external_evidence_item_blocked:real_order_backend_handoff" in completion_report["production_evidence"]["blockers"]


def test_production_evidence_initializer_refuses_repo_local_or_existing_outputs(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    repo_local_path = tmp_path / "ops-production-evidence.json"
    existing_path = _outside_repo_evidence_path(tmp_path, "existing-production-evidence.json")
    _write(existing_path, "{}")

    repo_local_report = completion_audit.write_external_acceptance_evidence_template(
        repo_local_path,
        repo_root=tmp_path,
    )
    existing_report = completion_audit.write_external_acceptance_evidence_template(
        existing_path,
        repo_root=tmp_path,
    )

    assert repo_local_report["created"] is False
    assert "external_evidence_output_must_be_outside_repo" in repo_local_report["blockers"]
    assert existing_report["created"] is False
    assert "external_evidence_output_exists" in existing_report["blockers"]


def test_completion_audit_blocks_local_acceptance_when_db_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_db_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Default production readiness DB-audit gate remains blocked" in runner_evidence["missing_phrases"]
    assert "--include-db-audits" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_frontend_source_guard_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_frontend_source_guard=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "tests/test_ai_trading_frontend_readiness_source.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_explain_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_production_evidence_explain_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Production evidence explain mode gate" in runner_evidence["missing_phrases"]
    assert "--explain-production-evidence" in runner_evidence["missing_phrases"]
    assert "production_evidence_explain_gate" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_admin_explain_api_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_explain_api_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence explain API | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_evidence_ui_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_ui_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence UI | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_validation_api_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_validation_api_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence validation API | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_validation_ui_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_validation_ui_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence validation UI | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_template_api_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_template_api_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence template API | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_template_ui_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_template_ui_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence template UI | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_payload_bounds_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_payload_bounds_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence payload bounds | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_agent_session_response_redaction_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_agent_session_response_context_redaction_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading agent-session response context redaction | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_session_context_prompt_sanitizer_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_session_context_prompt_sanitizer_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend session context prompt sanitizer | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_model_adjust_untrusted_context_boundary_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_adjust_untrusted_context_boundary_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model-adjust untrusted context boundary | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_model_adjust_output_sanitizer_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_adjust_output_sanitizer_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model-adjust output sanitizer | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_model_adjust_output_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_model_adjust_output_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend model-adjust output safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_validation_warning_labels_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_validation_warning_labels_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend validation warning labels | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_branch_is_not_thread_branch(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, git_branch="main")

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "git_governance" in report["summary"]["local_blockers"]
    assert report["git_governance"]["current_branch"] == "main"
    assert "unexpected_branch" in report["git_governance"]["blockers"]


def test_completion_audit_requires_external_pending_markers(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_external_markers=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "real_model_profile_live_acceptance" in report["summary"]["missing_external_markers"]
    assert "real_order_backend_handoff" in report["summary"]["missing_external_markers"]


def test_completion_audit_validates_production_evidence_but_requires_explicit_live_ready_confirmation(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    evidence_path = _outside_repo_evidence_path(tmp_path, "production-evidence.json")
    _write_production_evidence(evidence_path)

    report_without_confirmation = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=evidence_path,
    )

    assert report_without_confirmation["local_v1_accepted"] is True
    assert report_without_confirmation["production_evidence"]["ready"] is True
    assert report_without_confirmation["production_evidence"]["accepted_count"] == len(completion_audit.EXTERNAL_REQUIREMENTS)
    assert report_without_confirmation["ready_for_live_orders"] is False
    assert report_without_confirmation["summary"]["external_pending_count"] == 0
    assert report_without_confirmation["summary"]["documented_external_pending_count"] == len(completion_audit.EXTERNAL_REQUIREMENTS)
    assert (
        report_without_confirmation["summary"]["production_track"]
        == "external_evidence_accepted_pending_explicit_confirmation"
    )

    report_with_confirmation = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=evidence_path,
        allow_live_ready_from_evidence=True,
    )

    assert report_with_confirmation["ready_for_live_orders"] is True
    assert report_with_confirmation["summary"]["production_track"] == "accepted"
    assert report_with_confirmation["summary"]["external_pending_count"] == 0


def test_completion_audit_rejects_repo_local_production_evidence_file(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    evidence_path = tmp_path / "production-evidence.json"
    _write_production_evidence(evidence_path)

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=evidence_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    assert report["production_evidence"]["file_inside_repo"] is True
    assert "external_evidence_file_must_be_outside_repo" in report["production_evidence"]["blockers"]


def test_completion_audit_rejects_incomplete_or_secret_bearing_production_evidence(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    incomplete_path = tmp_path / "incomplete-production-evidence.json"
    secret_path = tmp_path / "secret-production-evidence.json"
    _write_production_evidence(incomplete_path, missing_item="real_order_backend_handoff")
    _write_production_evidence(secret_path, include_secret=True)

    incomplete_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=incomplete_path,
        allow_live_ready_from_evidence=True,
    )
    secret_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=secret_path,
        allow_live_ready_from_evidence=True,
    )

    assert incomplete_report["ready_for_live_orders"] is False
    assert "external_evidence_item_blocked:real_order_backend_handoff" in incomplete_report["production_evidence"]["blockers"]
    assert secret_report["ready_for_live_orders"] is False
    assert "external_evidence_secret_pattern_detected" in secret_report["production_evidence"]["blockers"]
    secret_item = next(item for item in secret_report["production_evidence"]["items"] if item["id"] == "real_order_backend_handoff")
    assert "external_evidence_secret_pattern_detected" in secret_item["blockers"]


def test_completion_audit_rejects_malformed_production_evidence_timestamps(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    missing_generated_path = tmp_path / "missing-generated-at-evidence.json"
    invalid_validated_path = tmp_path / "invalid-validated-at-evidence.json"
    timezone_missing_path = tmp_path / "timezone-missing-evidence.json"
    generated_before_validated_path = tmp_path / "generated-before-validated-evidence.json"
    _write_production_evidence(missing_generated_path, generated_at=None)
    _write_production_evidence(invalid_validated_path, validated_at="2026/06/10 12:00 UTC")
    _write_production_evidence(timezone_missing_path, generated_at="2026-06-10T12:05:00")
    _write_production_evidence(
        generated_before_validated_path,
        generated_at="2026-06-10T12:00:00Z",
        validated_at="2026-06-10T12:05:00Z",
    )

    missing_generated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=missing_generated_path,
        allow_live_ready_from_evidence=True,
    )
    invalid_validated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=invalid_validated_path,
        allow_live_ready_from_evidence=True,
    )
    timezone_missing_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=timezone_missing_path,
        allow_live_ready_from_evidence=True,
    )
    generated_before_validated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=generated_before_validated_path,
        allow_live_ready_from_evidence=True,
    )

    assert missing_generated_report["ready_for_live_orders"] is False
    assert "external_evidence_generated_at_missing" in missing_generated_report["production_evidence"]["blockers"]
    assert invalid_validated_report["ready_for_live_orders"] is False
    invalid_item = next(
        item
        for item in invalid_validated_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_at_invalid" in invalid_item["blockers"]
    assert timezone_missing_report["ready_for_live_orders"] is False
    assert "external_evidence_generated_at_timezone_missing" in timezone_missing_report["production_evidence"]["blockers"]
    assert generated_before_validated_report["ready_for_live_orders"] is False
    generated_before_validated_item = next(
        item
        for item in generated_before_validated_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_at_after_generated_at" in generated_before_validated_item["blockers"]


def test_completion_audit_rejects_unexpected_production_evidence_fields(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    root_extra_path = tmp_path / "root-extra-evidence.json"
    item_extra_path = tmp_path / "item-extra-evidence.json"
    _write_production_evidence(root_extra_path, root_extra={"raw_output": "sanitized but not schema-approved"})
    _write_production_evidence(item_extra_path, item_extra={"raw_trace": {"accepted": True}})

    root_extra_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=root_extra_path,
        allow_live_ready_from_evidence=True,
    )
    item_extra_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=item_extra_path,
        allow_live_ready_from_evidence=True,
    )

    assert root_extra_report["ready_for_live_orders"] is False
    assert "external_evidence_unexpected_root_fields" in root_extra_report["production_evidence"]["blockers"]
    assert root_extra_report["production_evidence"]["unexpected_fields"] == ["raw_output"]
    assert item_extra_report["ready_for_live_orders"] is False
    item_extra = next(
        item
        for item in item_extra_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_unexpected_item_fields" in item_extra["blockers"]
    assert item_extra["unexpected_fields"] == ["raw_trace"]


def test_completion_audit_rejects_unexpected_production_evidence_item_ids(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    evidence_path = tmp_path / "unexpected-item-id-evidence.json"
    _write_production_evidence(evidence_path)
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    payload["items"]["legacy_manual_acceptance"] = {
        "status": "accepted",
        "validated_at": "2026-06-10T12:00:00Z",
        "validated_by": "ops-admin",
        "evidence_summary": "Legacy acceptance item should not be accepted by the production schema.",
        "artifact_refs": ["ops://ai-trading/legacy-manual-acceptance"],
        "secret_values_returned": False,
    }
    _write(evidence_path, json.dumps(payload, indent=2, sort_keys=True))

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=evidence_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    assert "external_evidence_unexpected_item_ids" in report["production_evidence"]["blockers"]
    assert report["production_evidence"]["unexpected_item_ids"] == ["legacy_manual_acceptance"]


def test_completion_audit_rejects_unsafe_production_evidence_notes(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    scalar_notes_path = tmp_path / "scalar-notes-evidence.json"
    long_note_path = tmp_path / "long-note-evidence.json"
    too_many_notes_path = tmp_path / "too-many-notes-evidence.json"
    _write_production_evidence(scalar_notes_path, root_extra={"notes": "raw acceptance log"})
    _write_production_evidence(long_note_path, root_extra={"notes": ["sanitized note " + ("x" * 400)]})
    _write_production_evidence(
        too_many_notes_path,
        root_extra={
            "notes": [
                f"sanitized acceptance note {index}"
                for index in range(completion_audit.MAX_PRODUCTION_EVIDENCE_NOTES + 1)
            ]
        },
    )

    scalar_notes_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=scalar_notes_path,
        allow_live_ready_from_evidence=True,
    )
    long_note_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=long_note_path,
        allow_live_ready_from_evidence=True,
    )
    too_many_notes_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=too_many_notes_path,
        allow_live_ready_from_evidence=True,
    )

    assert scalar_notes_report["ready_for_live_orders"] is False
    assert "external_evidence_notes_must_be_list" in scalar_notes_report["production_evidence"]["blockers"]
    assert long_note_report["ready_for_live_orders"] is False
    assert "external_evidence_note_too_long" in long_note_report["production_evidence"]["blockers"]
    assert too_many_notes_report["ready_for_live_orders"] is False
    assert "external_evidence_notes_too_many" in too_many_notes_report["production_evidence"]["blockers"]


def test_completion_audit_rejects_placeholder_production_evidence_text(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    placeholder_path = tmp_path / "placeholder-evidence.json"
    short_path = tmp_path / "short-evidence.json"
    _write_production_evidence(
        placeholder_path,
        validated_by="TBD",
        evidence_summary="OK",
    )
    _write_production_evidence(
        short_path,
        validated_by="me",
        evidence_summary="accepted",
    )

    placeholder_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=placeholder_path,
        allow_live_ready_from_evidence=True,
    )
    short_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=short_path,
        allow_live_ready_from_evidence=True,
    )

    assert placeholder_report["ready_for_live_orders"] is False
    placeholder_item = next(
        item
        for item in placeholder_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_by_placeholder" in placeholder_item["blockers"]
    assert "external_evidence_summary_placeholder" in placeholder_item["blockers"]
    assert "external_evidence_summary_too_short" in placeholder_item["blockers"]
    assert short_report["ready_for_live_orders"] is False
    short_item = next(
        item
        for item in short_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_by_too_short" in short_item["blockers"]
    assert "external_evidence_summary_placeholder" in short_item["blockers"]
    assert "external_evidence_summary_too_short" in short_item["blockers"]


def test_completion_audit_rejects_overlong_production_evidence_text(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    evidence_path = tmp_path / "overlong-evidence.json"
    _write_production_evidence(
        evidence_path,
        validated_by="ops-" + ("reviewer" * 20),
        evidence_summary="sanitized evidence summary " + ("x" * 700),
    )

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=evidence_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    item = next(
        item
        for item in report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_by_too_long" in item["blockers"]
    assert "external_evidence_summary_too_long" in item["blockers"]


def test_completion_audit_rejects_unsafe_artifact_refs(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    empty_ref_path = tmp_path / "empty-artifact-ref-evidence.json"
    local_ref_path = tmp_path / "local-artifact-ref-evidence.json"
    credentials_ref_path = tmp_path / "credentials-artifact-ref-evidence.json"
    _write_production_evidence(empty_ref_path, empty_artifact_refs=True)
    _write_production_evidence(local_ref_path, artifact_ref_override="http://127.0.0.1:8802/internal-proof")
    _write_production_evidence(credentials_ref_path, artifact_ref_override="https://user:password@example.com/proof")

    empty_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=empty_ref_path,
        allow_live_ready_from_evidence=True,
    )
    local_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=local_ref_path,
        allow_live_ready_from_evidence=True,
    )
    credentials_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=credentials_ref_path,
        allow_live_ready_from_evidence=True,
    )

    assert empty_ref_report["ready_for_live_orders"] is False
    empty_ref_item = next(
        item
        for item in empty_ref_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_refs_empty" in empty_ref_item["blockers"]
    assert local_ref_report["ready_for_live_orders"] is False
    assert "external_evidence_item_blocked:real_order_backend_handoff" in local_ref_report["production_evidence"]["blockers"]
    local_ref_item = next(
        item
        for item in local_ref_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_ref_scheme_not_allowed" in local_ref_item["blockers"]
    assert "external_evidence_artifact_ref_local_host" in local_ref_item["blockers"]
    assert credentials_ref_report["ready_for_live_orders"] is False
    credentials_item = next(
        item
        for item in credentials_ref_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_ref_credentials_embedded" in credentials_item["blockers"]


def test_completion_audit_rejects_overlong_or_too_many_artifact_refs(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    overlong_ref_path = tmp_path / "overlong-artifact-ref-evidence.json"
    too_many_refs_path = tmp_path / "too-many-artifact-refs-evidence.json"
    _write_production_evidence(
        overlong_ref_path,
        artifact_ref_override="ops://ai-trading/" + ("x" * 400),
    )
    _write_production_evidence(too_many_refs_path)
    payload = json.loads(too_many_refs_path.read_text(encoding="utf-8"))
    payload["items"]["real_order_backend_handoff"]["artifact_refs"] = [
        f"ops://ai-trading/real-order-backend-handoff/{index}"
        for index in range(completion_audit.MAX_PRODUCTION_EVIDENCE_ARTIFACT_REFS + 1)
    ]
    _write(too_many_refs_path, json.dumps(payload, indent=2, sort_keys=True))

    overlong_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=overlong_ref_path,
        allow_live_ready_from_evidence=True,
    )
    too_many_refs_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=too_many_refs_path,
        allow_live_ready_from_evidence=True,
    )

    assert overlong_ref_report["ready_for_live_orders"] is False
    overlong_item = next(
        item
        for item in overlong_ref_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_ref_too_long" in overlong_item["blockers"]
    assert too_many_refs_report["ready_for_live_orders"] is False
    too_many_item = next(
        item
        for item in too_many_refs_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_refs_too_many" in too_many_item["blockers"]
