import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_v1_completion_audit.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SCRIPT_PATH = REPO_ROOT / "scripts" / "local-dev" / "run_ai_trading_v1_local_acceptance.sh"
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_completion_audit", SCRIPT_PATH)
completion_audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = completion_audit
SPEC.loader.exec_module(completion_audit)

_UNSET = object()
_TRANSIENT_RESOURCE_MARKERS = (
    "Resource temporarily unavailable",
    "Failed to spawn",
    "fork failed",
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _runner_function_source() -> str:
    source = RUNNER_SCRIPT_PATH.read_text(encoding="utf-8")
    start = source.index("positive_int_or_default()")
    end = source.index('\ncd "$REPO_ROOT"', start)
    return source[start:end]


def _has_transient_resource_output(output: str) -> bool:
    return any(marker in output for marker in _TRANSIENT_RESOURCE_MARKERS)


def _run_subprocess_with_transient_retry(*popenargs, attempts: int = 3, **kwargs):
    last_result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(attempts):
        try:
            result = subprocess.run(*popenargs, **kwargs)
        except subprocess.CalledProcessError as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            if attempt < attempts - 1 and _has_transient_resource_output(output):
                time.sleep(1)
                continue
            raise
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


def _run_bash_script_with_transient_retry(script: str, attempts: int = 3) -> subprocess.CompletedProcess[str]:
    return _run_subprocess_with_transient_retry(
        ["bash", "-c", script],
        attempts=attempts,
        capture_output=True,
        text=True,
    )


def _utc_iso(offset: timedelta = timedelta()) -> str:
    value = datetime.now(timezone.utc) + offset
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_evidence_summary(item_id: str) -> str:
    required_terms = [
        term_group[0]
        for term_group in completion_audit.PRODUCTION_EVIDENCE_ITEM_REQUIRED_SUMMARY_TERMS[item_id]
    ]
    return (
        f"{item_id} accepted with sanitized operational evidence covering "
        + ", ".join(required_terms)
        + "."
    )


def _write_minimal_acceptance_repo(
    root: Path,
    *,
    include_db_gate: bool = True,
    include_local_dev_shell_syntax_gate: bool = True,
    include_local_acceptance_transient_retry_gate: bool = True,
    include_production_operator_preflight_gate: bool = True,
    include_production_evidence_prepared_initializer_gate: bool = True,
    include_production_operator_preflight_dirty_tree_marker: bool = True,
    include_production_operator_preflight_output_redaction_marker: bool = True,
    include_production_url_host_secret_redaction_marker: bool = True,
    include_production_url_port_safety_marker: bool = True,
    include_production_url_parse_error_safety_marker: bool = True,
    include_ai_stream_routes_regression_gate: bool = True,
    include_kline_routes_regression_gate: bool = True,
    include_kline_collector_safety_gate: bool = True,
    include_kline_maintenance_endpoint_safety_marker: bool = True,
    include_frontend_source_guard: bool = True,
    include_production_evidence_explain_gate: bool = True,
    include_admin_production_evidence_explain_api_marker: bool = True,
    include_admin_production_evidence_ui_marker: bool = True,
    include_admin_production_evidence_validation_api_marker: bool = True,
    include_admin_production_evidence_validation_ui_marker: bool = True,
    include_admin_production_evidence_template_api_marker: bool = True,
    include_admin_production_evidence_template_ui_marker: bool = True,
    include_admin_production_evidence_prepared_template_api_marker: bool = True,
    include_admin_production_evidence_prepared_template_ui_marker: bool = True,
    include_production_evidence_template_guidance_marker: bool = True,
    include_production_evidence_validation_guidance_marker: bool = True,
    include_production_evidence_root_guidance_marker: bool = True,
    include_production_evidence_root_actions_marker: bool = True,
    include_admin_production_evidence_payload_bounds_marker: bool = True,
    include_production_evidence_summary_terms_marker: bool = True,
    include_production_evidence_expiry_gate_marker: bool = True,
    include_production_evidence_expiry_window_marker: bool = True,
    include_production_evidence_cutover_approval_ref_marker: bool = True,
    include_production_evidence_future_timestamp_guard_marker: bool = True,
    include_production_evidence_validation_age_guard_marker: bool = True,
    include_production_evidence_cutover_window_guard_marker: bool = True,
    include_production_evidence_run_id_guard_marker: bool = True,
    include_production_evidence_run_id_traceability_marker: bool = True,
    include_production_evidence_item_artifact_traceability_marker: bool = True,
    include_production_evidence_artifact_ref_uniqueness_marker: bool = True,
    include_production_evidence_artifact_ref_item_uniqueness_marker: bool = True,
    include_production_evidence_blocker_labels_marker: bool = True,
    include_production_evidence_template_blocker_labels_marker: bool = True,
    include_production_evidence_explain_root_blocker_labels_marker: bool = True,
    include_production_evidence_progress_summary_marker: bool = True,
    include_production_evidence_progress_actions_marker: bool = True,
    include_production_evidence_progress_root_actions_marker: bool = True,
    include_production_evidence_prepared_initializer_marker: bool = True,
    include_production_evidence_dry_run_safety_metadata_marker: bool = True,
    include_production_evidence_non_object_dry_run_safety_marker: bool = True,
    include_production_evidence_frontend_error_safety_marker: bool = True,
    include_admin_ai_runtime_last_error_redaction_marker: bool = True,
    include_ai_stream_polling_error_redaction_marker: bool = True,
    include_frontend_ai_stream_polling_error_safety_marker: bool = True,
    include_frontend_ai_runtime_error_safety_marker: bool = True,
    include_frontend_production_readiness_error_safety_marker: bool = True,
    include_frontend_strategy_action_error_safety_marker: bool = True,
    include_frontend_backtest_metrics_json_error_safety_marker: bool = True,
    include_frontend_backtest_summary_inline_no_prompt_marker: bool = True,
    include_frontend_program_backtest_inline_no_prompt_marker: bool = True,
    include_frontend_program_backtest_run_inline_confirm_marker: bool = True,
    include_frontend_signal_handoff_inline_confirm_marker: bool = True,
    include_frontend_agent_session_archive_inline_confirm_marker: bool = True,
    include_hyperliquid_wallet_delete_inline_confirm_marker: bool = True,
    include_binance_wallet_delete_inline_confirm_marker: bool = True,
    include_frontend_prompt_packet_sanitizer_marker: bool = True,
    include_frontend_handoff_error_safety_marker: bool = True,
    include_frontend_agent_session_error_safety_marker: bool = True,
    include_local_supervisor_fork_resilience_marker: bool = True,
    include_env_check_docker_probe_fallback_marker: bool = True,
    include_agent_session_response_context_redaction_marker: bool = True,
    include_frontend_session_context_prompt_sanitizer_marker: bool = True,
    include_model_adjust_untrusted_context_boundary_marker: bool = True,
    include_model_adjust_output_sanitizer_marker: bool = True,
    include_frontend_model_adjust_output_safety_marker: bool = True,
    include_model_gateway_exception_type_safety_marker: bool = True,
    include_route_exception_detail_safety_marker: bool = True,
    include_hyper_ai_tool_error_safety_marker: bool = True,
    include_hyper_ai_service_stream_error_safety_marker: bool = True,
    include_hyper_ai_memory_error_safety_marker: bool = True,
    include_hyper_ai_memory_prompt_safety_marker: bool = True,
    include_hyper_ai_memory_storage_safety_marker: bool = True,
    include_hyper_ai_profile_safety_marker: bool = True,
    include_hyper_ai_suggestions_context_safety_marker: bool = True,
    include_hyper_ai_suggestions_output_safety_marker: bool = True,
    include_hyper_ai_llm_base_url_safety_marker: bool = True,
    include_hyper_ai_preset_endpoint_override_guard_marker: bool = True,
    include_hyper_ai_custom_endpoint_ssrf_guard_marker: bool = True,
    include_hyper_ai_llm_redirect_guard_marker: bool = True,
    include_shared_ai_llm_redirect_guard_regression_gate: bool = True,
    include_shared_ai_llm_redirect_guard_marker: bool = True,
    include_shared_ai_llm_tls_verification_guard_marker: bool = True,
    include_account_llm_connection_error_safety_regression_gate: bool = True,
    include_account_llm_connection_error_safety_marker: bool = True,
    include_account_hyperliquid_builder_error_safety_regression_gate: bool = True,
    include_account_hyperliquid_builder_error_safety_marker: bool = True,
    include_hyperliquid_wallet_error_safety_regression_gate: bool = True,
    include_hyperliquid_wallet_error_safety_marker: bool = True,
    include_hyperliquid_agent_wallet_error_safety_regression_gate: bool = True,
    include_hyperliquid_agent_wallet_error_safety_marker: bool = True,
    include_hyperliquid_auxiliary_error_safety_regression_gate: bool = True,
    include_hyperliquid_auxiliary_error_safety_marker: bool = True,
    include_hyperliquid_core_route_error_safety_regression_gate: bool = True,
    include_hyperliquid_core_route_error_safety_marker: bool = True,
    include_hyperliquid_execution_route_error_safety_regression_gate: bool = True,
    include_hyperliquid_execution_route_error_safety_marker: bool = True,
    include_hyperliquid_read_route_error_safety_regression_gate: bool = True,
    include_hyperliquid_read_route_error_safety_marker: bool = True,
    include_model_readiness_sensitive_endpoint_gate_marker: bool = True,
    include_context_compression_error_safety_marker: bool = True,
    include_context_compression_prompt_safety_marker: bool = True,
    include_frontend_validation_warning_labels_marker: bool = True,
    include_model_readiness_ui_source_guard_marker: bool = True,
    include_model_readiness_next_actions_marker: bool = True,
    include_model_setup_shortcut_marker: bool = True,
    include_model_setup_runtime_refresh_marker: bool = True,
    include_frontend_model_config_error_safety_marker: bool = True,
    include_frontend_onboarding_error_safety_marker: bool = True,
    include_frontend_onboarding_blank_page_guard_marker: bool = True,
    include_frontend_model_config_nonblocking_entry_marker: bool = True,
    include_frontend_main_page_api_key_config_entry_marker: bool = True,
    include_frontend_onboarding_api_key_deferral_marker: bool = True,
    include_frontend_public_asset_path_guard_marker: bool = True,
    include_frontend_bot_tool_config_error_safety_marker: bool = True,
    include_frontend_market_universe_error_safety_marker: bool = True,
    include_frontend_market_symbol_sanitizer_marker: bool = True,
    include_private_factor_per_user_result_schema_marker: bool = True,
    include_private_factor_precompute_writer_reader_marker: bool = True,
    include_private_factor_precompute_db_smoke_marker: bool = True,
    include_agent_session_id_safety_marker: bool = True,
    include_agent_session_id_validation_error_safety_marker: bool = True,
    include_agent_session_name_safety_marker: bool = True,
    include_strategy_spec_name_safety_marker: bool = True,
    include_handoff_error_message_safety_marker: bool = True,
    include_handoff_confirmation_source_safety_marker: bool = True,
    include_signal_rejection_reason_safety_marker: bool = True,
    include_backtest_evidence_safety_marker: bool = True,
    include_market_context_safety_marker: bool = True,
    include_strategy_text_source_safety_marker: bool = True,
    include_gateway_mode_guard_marker: bool = True,
    include_runtime_readiness_retry_grace_marker: bool = True,
    include_external_markers: bool = True,
    git_branch: str = "codex/ai-agent-multitenant-foundation",
) -> None:
    db_gate_text = (
        "Default production readiness DB-audit gate remains blocked\n"
        "--include-db-audits\n"
    ) if include_db_gate else ""
    local_dev_shell_syntax_text = (
        "Local dev shell syntax\n"
    ) if include_local_dev_shell_syntax_gate else ""
    local_acceptance_transient_retry_runner_text = (
        "AI_TRADING_TRANSIENT_RETRY_ATTEMPTS\n"
        "AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS\n"
        "Transient local resource failure\n"
        "run_command_with_transient_retry\n"
        "make_temp_file_with_retry\n"
        "Resource temporarily unavailable\n"
        "Failed to spawn\n"
        "fork failed\n"
    ) if include_local_acceptance_transient_retry_gate else ""
    local_acceptance_transient_retry_status_marker = (
        "| AI Trading local acceptance transient retry | Done |"
    ) if include_local_acceptance_transient_retry_gate else ""
    ai_stream_routes_regression_text = (
        "tests/test_ai_stream_routes.py\n"
    ) if include_ai_stream_routes_regression_gate else ""
    hyper_ai_service_error_safety_regression_text = (
        "tests/test_hyper_ai_service_error_safety.py\n"
    ) if include_hyper_ai_service_stream_error_safety_marker else ""
    hyper_ai_tool_error_safety_regression_text = (
        "tests/test_hyper_ai_tool_error_safety.py\n"
    ) if include_hyper_ai_tool_error_safety_marker else ""
    hyper_ai_memory_error_safety_regression_text = (
        "tests/test_hyper_ai_memory_error_safety.py\n"
    ) if include_hyper_ai_memory_error_safety_marker else ""
    hyper_ai_profile_safety_regression_text = (
        "tests/test_hyper_ai_profile_safety.py\n"
    ) if include_hyper_ai_profile_safety_marker else ""
    hyper_ai_suggestions_context_safety_regression_text = (
        "tests/test_hyper_ai_suggestions_context_safety.py\n"
    ) if include_hyper_ai_suggestions_context_safety_marker else ""
    hyper_ai_llm_base_url_safety_regression_text = (
        "tests/test_hyper_ai_llm_base_url_safety.py\n"
    ) if include_hyper_ai_llm_base_url_safety_marker else ""
    shared_ai_llm_redirect_guard_regression_text = (
        "tests/test_shared_ai_llm_redirect_guard.py\n"
        "services/llm_transport_security.py\n"
    ) if include_shared_ai_llm_redirect_guard_regression_gate else ""
    account_llm_connection_error_safety_regression_text = (
        "tests/test_account_llm_connection_error_safety.py\n"
    ) if include_account_llm_connection_error_safety_regression_gate else ""
    account_hyperliquid_builder_error_safety_regression_text = (
        "tests/test_account_hyperliquid_builder_error_safety.py\n"
    ) if include_account_hyperliquid_builder_error_safety_regression_gate else ""
    hyperliquid_wallet_error_safety_regression_text = (
        "tests/test_hyperliquid_wallet_error_safety.py\n"
    ) if include_hyperliquid_wallet_error_safety_regression_gate else ""
    hyperliquid_agent_wallet_error_safety_regression_text = (
        "tests/test_hyperliquid_agent_wallet_error_safety.py\n"
    ) if include_hyperliquid_agent_wallet_error_safety_regression_gate else ""
    hyperliquid_auxiliary_error_safety_regression_text = (
        "tests/test_hyperliquid_auxiliary_error_safety.py\n"
    ) if include_hyperliquid_auxiliary_error_safety_regression_gate else ""
    hyperliquid_core_route_error_safety_regression_text = (
        "tests/test_hyperliquid_core_route_error_safety.py\n"
    ) if include_hyperliquid_core_route_error_safety_regression_gate else ""
    hyperliquid_execution_route_error_safety_regression_text = (
        "tests/test_hyperliquid_execution_route_error_safety.py\n"
    ) if include_hyperliquid_execution_route_error_safety_regression_gate else ""
    hyperliquid_read_route_error_safety_regression_text = (
        "tests/test_hyperliquid_read_route_error_safety.py\n"
    ) if include_hyperliquid_read_route_error_safety_regression_gate else ""
    context_compression_error_safety_regression_text = (
        "tests/test_ai_context_compression_error_safety.py\n"
    ) if include_context_compression_error_safety_marker else ""
    kline_routes_regression_text = (
        "tests/test_kline_routes.py\n"
    ) if include_kline_routes_regression_gate else ""
    kline_collectors_regression_text = (
        "tests/test_kline_collectors.py\n"
    ) if include_kline_collector_safety_gate else ""
    frontend_source_guard_text = (
        "tests/test_ai_trading_frontend_readiness_source.py\n"
    ) if include_frontend_source_guard else ""
    explain_gate_text = (
        "Production evidence explain mode gate\n"
        "--explain-production-evidence\n"
        "production_evidence_explain_gate\n"
    ) if include_production_evidence_explain_gate else ""
    prepared_initializer_gate_text = (
        "Production evidence prepared initializer gate\n"
        "--prepare-production-evidence-file\n"
        "production_evidence_prepared_initializer_gate\n"
    ) if include_production_evidence_prepared_initializer_gate else ""
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
    admin_prepared_template_api_marker = (
        "| AI Trading admin production evidence prepared template API | Done |"
    ) if include_admin_production_evidence_prepared_template_api_marker else ""
    admin_prepared_template_ui_marker = (
        "| AI Trading admin production evidence prepared template UI | Done |"
    ) if include_admin_production_evidence_prepared_template_ui_marker else ""
    production_evidence_template_guidance_marker = (
        "| AI Trading production evidence template guidance | Done |"
    ) if include_production_evidence_template_guidance_marker else ""
    production_evidence_validation_guidance_marker = (
        "| AI Trading production evidence validation guidance | Done |"
    ) if include_production_evidence_validation_guidance_marker else ""
    production_evidence_root_guidance_marker = (
        "| AI Trading production evidence root guidance | Done |"
    ) if include_production_evidence_root_guidance_marker else ""
    production_evidence_root_actions_marker = (
        "| AI Trading production evidence root actions | Done |"
    ) if include_production_evidence_root_actions_marker else ""
    admin_payload_bounds_marker = (
        "| AI Trading admin production evidence payload bounds | Done |"
    ) if include_admin_production_evidence_payload_bounds_marker else ""
    production_evidence_summary_terms_marker = (
        "| AI Trading production evidence summary terms | Done |"
    ) if include_production_evidence_summary_terms_marker else ""
    production_evidence_expiry_gate_marker = (
        "| AI Trading production evidence expiry gate | Done |"
    ) if include_production_evidence_expiry_gate_marker else ""
    production_evidence_expiry_window_marker = (
        "| AI Trading production evidence expiry window | Done |"
    ) if include_production_evidence_expiry_window_marker else ""
    production_evidence_cutover_approval_ref_marker = (
        "| AI Trading production evidence cutover approval ref | Done |"
    ) if include_production_evidence_cutover_approval_ref_marker else ""
    production_evidence_future_timestamp_guard_marker = (
        "| AI Trading production evidence future timestamp guard | Done |"
    ) if include_production_evidence_future_timestamp_guard_marker else ""
    production_evidence_validation_age_guard_marker = (
        "| AI Trading production evidence validation age guard | Done |"
    ) if include_production_evidence_validation_age_guard_marker else ""
    production_evidence_cutover_window_guard_marker = (
        "| AI Trading production evidence cutover window guard | Done |"
    ) if include_production_evidence_cutover_window_guard_marker else ""
    production_evidence_run_id_guard_marker = (
        "| AI Trading production evidence run id guard | Done |"
    ) if include_production_evidence_run_id_guard_marker else ""
    production_evidence_run_id_traceability_marker = (
        "| AI Trading production evidence run id traceability | Done |"
    ) if include_production_evidence_run_id_traceability_marker else ""
    production_evidence_item_artifact_traceability_marker = (
        "| AI Trading production evidence item artifact traceability | Done |"
    ) if include_production_evidence_item_artifact_traceability_marker else ""
    production_evidence_artifact_ref_uniqueness_marker = (
        "| AI Trading production evidence artifact ref uniqueness | Done |"
    ) if include_production_evidence_artifact_ref_uniqueness_marker else ""
    production_evidence_artifact_ref_item_uniqueness_marker = (
        "| AI Trading production evidence artifact ref item uniqueness | Done |"
    ) if include_production_evidence_artifact_ref_item_uniqueness_marker else ""
    production_evidence_blocker_labels_marker = (
        "| AI Trading production evidence blocker labels | Done |"
    ) if include_production_evidence_blocker_labels_marker else ""
    production_evidence_template_blocker_labels_marker = (
        "| AI Trading production evidence template blocker labels | Done |"
    ) if include_production_evidence_template_blocker_labels_marker else ""
    production_evidence_explain_root_blocker_labels_marker = (
        "| AI Trading production evidence explain root blocker labels | Done |"
    ) if include_production_evidence_explain_root_blocker_labels_marker else ""
    production_evidence_progress_summary_marker = (
        "| AI Trading production evidence progress summary | Done |"
    ) if include_production_evidence_progress_summary_marker else ""
    production_evidence_progress_actions_marker = (
        "| AI Trading production evidence progress actions | Done |"
    ) if include_production_evidence_progress_actions_marker else ""
    production_evidence_progress_root_actions_marker = (
        "| AI Trading production evidence progress root actions | Done |"
    ) if include_production_evidence_progress_root_actions_marker else ""
    production_evidence_prepared_initializer_marker = (
        "| AI Trading production evidence prepared initializer | Done |"
    ) if include_production_evidence_prepared_initializer_marker else ""
    production_evidence_dry_run_safety_metadata_marker = (
        "| AI Trading production evidence dry-run safety metadata | Done |"
    ) if include_production_evidence_dry_run_safety_metadata_marker else ""
    production_evidence_non_object_dry_run_safety_marker = (
        "| AI Trading production evidence non-object dry-run safety | Done |"
    ) if include_production_evidence_non_object_dry_run_safety_marker else ""
    production_evidence_frontend_error_safety_marker = (
        "| AI Trading production evidence frontend error safety | Done |"
    ) if include_production_evidence_frontend_error_safety_marker else ""
    admin_ai_runtime_last_error_redaction_marker = (
        "| AI Trading admin AI runtime last-error redaction | Done |"
    ) if include_admin_ai_runtime_last_error_redaction_marker else ""
    ai_stream_polling_error_redaction_marker = (
        "| AI Trading AI stream polling error redaction | Done |"
    ) if include_ai_stream_polling_error_redaction_marker else ""
    frontend_ai_stream_polling_error_safety_marker = (
        "| AI Trading frontend AI stream polling error safety | Done |"
    ) if include_frontend_ai_stream_polling_error_safety_marker else ""
    frontend_ai_runtime_error_safety_marker = (
        "| AI Trading frontend AI runtime error safety | Done |"
    ) if include_frontend_ai_runtime_error_safety_marker else ""
    frontend_production_readiness_error_safety_marker = (
        "| AI Trading frontend production-readiness error safety | Done |"
    ) if include_frontend_production_readiness_error_safety_marker else ""
    frontend_strategy_action_error_safety_marker = (
        "| AI Trading frontend strategy-action error safety | Done |"
    ) if include_frontend_strategy_action_error_safety_marker else ""
    frontend_backtest_metrics_json_error_safety_marker = (
        "| AI Trading frontend backtest metrics JSON error safety | Done |"
    ) if include_frontend_backtest_metrics_json_error_safety_marker else ""
    frontend_backtest_summary_inline_no_prompt_marker = (
        "| AI Trading frontend backtest summary inline no-prompt | Done |"
    ) if include_frontend_backtest_summary_inline_no_prompt_marker else ""
    frontend_program_backtest_inline_no_prompt_marker = (
        "| AI Trading frontend program backtest inline no-prompt | Done |"
    ) if include_frontend_program_backtest_inline_no_prompt_marker else ""
    frontend_program_backtest_run_inline_confirm_marker = (
        "| AI Trading frontend program backtest run inline confirm | Done |"
    ) if include_frontend_program_backtest_run_inline_confirm_marker else ""
    frontend_signal_handoff_inline_confirm_marker = (
        "| AI Trading frontend signal handoff inline confirm | Done |"
    ) if include_frontend_signal_handoff_inline_confirm_marker else ""
    frontend_agent_session_archive_inline_confirm_marker = (
        "| AI Trading frontend agent-session archive inline confirm | Done |"
    ) if include_frontend_agent_session_archive_inline_confirm_marker else ""
    hyperliquid_wallet_delete_inline_confirm_marker = (
        "| AI Trading Hyperliquid wallet delete inline confirm | Done |"
    ) if include_hyperliquid_wallet_delete_inline_confirm_marker else ""
    binance_wallet_delete_inline_confirm_marker = (
        "| AI Trading Binance wallet delete inline confirm | Done |"
    ) if include_binance_wallet_delete_inline_confirm_marker else ""
    frontend_prompt_packet_sanitizer_marker = (
        "| AI Trading frontend prompt-packet sanitizer | Done |"
    ) if include_frontend_prompt_packet_sanitizer_marker else ""
    frontend_handoff_error_safety_marker = (
        "| AI Trading frontend handoff error safety | Done |"
    ) if include_frontend_handoff_error_safety_marker else ""
    frontend_agent_session_error_safety_marker = (
        "| AI Trading frontend agent-session error safety | Done |"
    ) if include_frontend_agent_session_error_safety_marker else ""
    local_supervisor_fork_resilience_marker = (
        "| AI Trading local supervisor fork-pressure resilience | Done |"
    ) if include_local_supervisor_fork_resilience_marker else ""
    env_check_docker_probe_fallback_marker = (
        "| AI Trading env-check Docker probe fallback | Done |"
    ) if include_env_check_docker_probe_fallback_marker else ""
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
    model_gateway_exception_type_safety_marker = (
        "| AI Trading model/gateway exception type safety | Done |"
    ) if include_model_gateway_exception_type_safety_marker else ""
    route_exception_detail_safety_marker = (
        "| AI Trading route exception detail safety | Done |"
    ) if include_route_exception_detail_safety_marker else ""
    hyper_ai_tool_error_safety_marker = (
        "| AI Trading Hyper AI tool error safety | Done |"
    ) if include_hyper_ai_tool_error_safety_marker else ""
    hyper_ai_service_stream_error_safety_marker = (
        "| AI Trading Hyper AI service stream error safety | Done |"
    ) if include_hyper_ai_service_stream_error_safety_marker else ""
    hyper_ai_memory_error_safety_marker = (
        "| AI Trading Hyper AI memory error safety | Done |"
    ) if include_hyper_ai_memory_error_safety_marker else ""
    hyper_ai_memory_prompt_safety_marker = (
        "| AI Trading Hyper AI memory prompt safety | Done |"
    ) if include_hyper_ai_memory_prompt_safety_marker else ""
    hyper_ai_memory_storage_safety_marker = (
        "| AI Trading Hyper AI memory storage safety | Done |"
    ) if include_hyper_ai_memory_storage_safety_marker else ""
    hyper_ai_profile_safety_marker = (
        "| AI Trading Hyper AI profile safety | Done |"
    ) if include_hyper_ai_profile_safety_marker else ""
    hyper_ai_suggestions_context_safety_marker = (
        "| AI Trading Hyper AI suggestions context safety | Done |"
    ) if include_hyper_ai_suggestions_context_safety_marker else ""
    hyper_ai_suggestions_output_safety_marker = (
        "| AI Trading Hyper AI suggestions output safety | Done |"
    ) if include_hyper_ai_suggestions_output_safety_marker else ""
    hyper_ai_llm_base_url_safety_marker = (
        "| AI Trading Hyper AI LLM base URL safety | Done |"
    ) if include_hyper_ai_llm_base_url_safety_marker else ""
    hyper_ai_preset_endpoint_override_guard_marker = (
        "| AI Trading Hyper AI preset endpoint override guard | Done |"
    ) if include_hyper_ai_preset_endpoint_override_guard_marker else ""
    hyper_ai_custom_endpoint_ssrf_guard_marker = (
        "| AI Trading Hyper AI custom endpoint SSRF guard | Done |"
    ) if include_hyper_ai_custom_endpoint_ssrf_guard_marker else ""
    hyper_ai_llm_redirect_guard_marker = (
        "| AI Trading Hyper AI LLM redirect guard | Done |"
    ) if include_hyper_ai_llm_redirect_guard_marker else ""
    shared_ai_llm_redirect_guard_marker = (
        "| AI Trading shared AI LLM redirect guard | Done |"
    ) if include_shared_ai_llm_redirect_guard_marker else ""
    shared_ai_llm_tls_verification_guard_marker = (
        "| AI Trading shared AI LLM TLS verification guard | Done |"
    ) if include_shared_ai_llm_tls_verification_guard_marker else ""
    account_llm_connection_error_safety_marker = (
        "| AI Trading account LLM connection error safety | Done |"
    ) if include_account_llm_connection_error_safety_marker else ""
    account_hyperliquid_builder_error_safety_marker = (
        "| AI Trading account Hyperliquid builder error safety | Done |"
    ) if include_account_hyperliquid_builder_error_safety_marker else ""
    hyperliquid_wallet_error_safety_marker = (
        "| AI Trading Hyperliquid private-key wallet error safety | Done |"
    ) if include_hyperliquid_wallet_error_safety_marker else ""
    hyperliquid_agent_wallet_error_safety_marker = (
        "| AI Trading Hyperliquid agent-wallet error safety | Done |"
    ) if include_hyperliquid_agent_wallet_error_safety_marker else ""
    hyperliquid_auxiliary_error_safety_marker = (
        "| AI Trading Hyperliquid auxiliary route error safety | Done |"
    ) if include_hyperliquid_auxiliary_error_safety_marker else ""
    hyperliquid_core_route_error_safety_marker = (
        "| AI Trading Hyperliquid core route error safety | Done |"
    ) if include_hyperliquid_core_route_error_safety_marker else ""
    hyperliquid_execution_route_error_safety_marker = (
        "| AI Trading Hyperliquid execution route error safety | Done |"
    ) if include_hyperliquid_execution_route_error_safety_marker else ""
    hyperliquid_read_route_error_safety_marker = (
        "| AI Trading Hyperliquid read route error safety | Done |"
    ) if include_hyperliquid_read_route_error_safety_marker else ""
    model_readiness_sensitive_endpoint_gate_marker = (
        "| AI Trading model readiness sensitive endpoint gate | Done |"
    ) if include_model_readiness_sensitive_endpoint_gate_marker else ""
    context_compression_error_safety_marker = (
        "| AI Trading context compression error safety | Done |"
    ) if include_context_compression_error_safety_marker else ""
    context_compression_prompt_safety_marker = (
        "| AI Trading context compression prompt safety | Done |"
    ) if include_context_compression_prompt_safety_marker else ""
    frontend_validation_warning_labels_marker = (
        "| AI Trading frontend validation warning labels | Done |"
    ) if include_frontend_validation_warning_labels_marker else ""
    model_readiness_ui_source_guard_marker = (
        "| AI Trading model readiness UI source guard | Done |"
    ) if include_model_readiness_ui_source_guard_marker else ""
    model_readiness_next_actions_marker = (
        "| AI Trading model readiness next actions | Done |"
    ) if include_model_readiness_next_actions_marker else ""
    model_setup_shortcut_marker = (
        "| AI Trading model setup shortcut | Done |"
    ) if include_model_setup_shortcut_marker else ""
    model_setup_runtime_refresh_marker = (
        "| AI Trading model setup runtime refresh | Done |"
    ) if include_model_setup_runtime_refresh_marker else ""
    frontend_model_config_error_safety_marker = (
        "| AI Trading frontend model-config error safety | Done |"
    ) if include_frontend_model_config_error_safety_marker else ""
    frontend_onboarding_error_safety_marker = (
        "| AI Trading frontend onboarding error safety | Done |"
    ) if include_frontend_onboarding_error_safety_marker else ""
    frontend_onboarding_blank_page_guard_marker = (
        "| AI Trading frontend onboarding blank-page guard | Done |"
    ) if include_frontend_onboarding_blank_page_guard_marker else ""
    frontend_model_config_nonblocking_entry_marker = (
        "| AI Trading frontend model-config nonblocking entry | Done |"
    ) if include_frontend_model_config_nonblocking_entry_marker else ""
    frontend_main_page_api_key_config_entry_marker = (
        "| AI Trading frontend main-page API-key config entry | Done |"
    ) if include_frontend_main_page_api_key_config_entry_marker else ""
    frontend_onboarding_api_key_deferral_marker = (
        "| AI Trading frontend onboarding API-key deferral | Done |"
    ) if include_frontend_onboarding_api_key_deferral_marker else ""
    frontend_public_asset_path_guard_marker = (
        "| AI Trading frontend public asset path guard | Done |"
    ) if include_frontend_public_asset_path_guard_marker else ""
    frontend_bot_tool_config_error_safety_marker = (
        "| AI Trading frontend bot/tool config error safety | Done |"
    ) if include_frontend_bot_tool_config_error_safety_marker else ""
    frontend_market_universe_error_safety_marker = (
        "| AI Trading frontend market-universe error safety | Done |"
    ) if include_frontend_market_universe_error_safety_marker else ""
    frontend_market_symbol_sanitizer_marker = (
        "| AI Trading frontend market symbol sanitizer | Done |"
    ) if include_frontend_market_symbol_sanitizer_marker else ""
    kline_local_db_api_marker = (
        "| AI Trading K-line local DB API | Done |"
    ) if include_kline_routes_regression_gate else ""
    kline_collector_safety_marker = (
        "| AI Trading K-line collector/backfill safety | Done |"
    ) if include_kline_collector_safety_gate else ""
    kline_maintenance_endpoint_safety_marker = (
        "| AI Trading K-line maintenance endpoint safety | Done |"
    ) if include_kline_maintenance_endpoint_safety_marker else ""
    private_factor_per_user_result_schema_marker = (
        "| AI Trading private factor per-user result schema | Done |"
    ) if include_private_factor_per_user_result_schema_marker else ""
    private_factor_precompute_writer_reader_marker = (
        "| AI Trading private factor precompute writer-reader | Done |"
    ) if include_private_factor_precompute_writer_reader_marker else ""
    private_factor_precompute_db_smoke_marker = (
        "| AI Trading private factor precompute DB smoke | Done |"
    ) if include_private_factor_precompute_db_smoke_marker else ""
    agent_session_id_safety_marker = (
        "| AI Trading agent-session id safety | Done |"
    ) if include_agent_session_id_safety_marker else ""
    agent_session_id_validation_error_safety_marker = (
        "| AI Trading agent-session id validation error safety | Done |"
    ) if include_agent_session_id_validation_error_safety_marker else ""
    agent_session_name_safety_marker = (
        "| AI Trading agent-session name safety | Done |"
    ) if include_agent_session_name_safety_marker else ""
    strategy_spec_name_safety_marker = (
        "| AI Trading strategy-spec name safety | Done |"
    ) if include_strategy_spec_name_safety_marker else ""
    handoff_error_message_safety_marker = (
        "| AI Trading handoff error-message safety | Done |"
    ) if include_handoff_error_message_safety_marker else ""
    handoff_confirmation_source_safety_marker = (
        "| AI Trading handoff confirmation-source safety | Done |"
    ) if include_handoff_confirmation_source_safety_marker else ""
    signal_rejection_reason_safety_marker = (
        "| AI Trading signal rejection reason safety | Done |"
    ) if include_signal_rejection_reason_safety_marker else ""
    backtest_evidence_safety_marker = (
        "| AI Trading backtest evidence safety | Done |"
    ) if include_backtest_evidence_safety_marker else ""
    market_context_safety_marker = (
        "| AI Trading market context safety | Done |"
    ) if include_market_context_safety_marker else ""
    strategy_text_source_safety_marker = (
        "| AI Trading strategy text source safety | Done |"
    ) if include_strategy_text_source_safety_marker else ""
    gateway_mode_guard_marker = (
        "| AI Trading gateway mode guard | Done |"
    ) if include_gateway_mode_guard_marker else ""
    runtime_readiness_retry_grace_runner_text = (
        "AI_TRADING_RUNTIME_READINESS_ATTEMPTS\n"
        "AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS\n"
        "Runtime readiness still blocked\n"
    ) if include_runtime_readiness_retry_grace_marker else ""
    runtime_readiness_retry_grace_status_marker = (
        "| AI Trading runtime readiness retry grace | Done |"
    ) if include_runtime_readiness_retry_grace_marker else ""
    production_operator_preflight_runner_text = (
        "Production operator preflight remains blocked\n"
        "ai_trading_v1_production_operator_preflight.py --skip-local-runtime --strict\n"
        "production_operator_preflight_gate\n"
        "completion:live_orders_not_ready\n"
        "REDACTED_SENSITIVE_PREFLIGHT_VALUE\n"
    ) if include_production_operator_preflight_gate else ""
    production_operator_preflight_status_marker = (
        "| AI Trading production operator preflight | Done |"
    ) if include_production_operator_preflight_gate else ""
    production_operator_preflight_dirty_tree_status_marker = (
        "| AI Trading production operator preflight dirty-tree blocker | Done |"
    ) if include_production_operator_preflight_dirty_tree_marker else ""
    production_operator_preflight_output_redaction_status_marker = (
        "| AI Trading production operator preflight output redaction | Done |"
    ) if include_production_operator_preflight_output_redaction_marker else ""
    production_url_host_secret_redaction_status_marker = (
        "| AI Trading production URL host secret redaction | Done |"
    ) if include_production_url_host_secret_redaction_marker else ""
    production_url_port_safety_status_marker = (
        "| AI Trading production URL port safety | Done |"
    ) if include_production_url_port_safety_marker else ""
    production_url_parse_error_safety_status_marker = (
        "| AI Trading production URL parse-error safety | Done |"
    ) if include_production_url_parse_error_safety_marker else ""
    _write(
        root / "scripts/local-dev/run_ai_trading_v1_local_acceptance.sh",
        "\n".join(
            [
                "--confirm-local-mock-handoff",
                local_dev_shell_syntax_text,
                local_acceptance_transient_retry_runner_text,
                db_gate_text,
                ai_stream_routes_regression_text,
                hyper_ai_service_error_safety_regression_text,
                hyper_ai_tool_error_safety_regression_text,
                hyper_ai_memory_error_safety_regression_text,
                hyper_ai_profile_safety_regression_text,
                hyper_ai_suggestions_context_safety_regression_text,
                hyper_ai_llm_base_url_safety_regression_text,
                shared_ai_llm_redirect_guard_regression_text,
                account_llm_connection_error_safety_regression_text,
                account_hyperliquid_builder_error_safety_regression_text,
                hyperliquid_wallet_error_safety_regression_text,
                hyperliquid_agent_wallet_error_safety_regression_text,
                hyperliquid_auxiliary_error_safety_regression_text,
                hyperliquid_core_route_error_safety_regression_text,
                hyperliquid_execution_route_error_safety_regression_text,
                hyperliquid_read_route_error_safety_regression_text,
                context_compression_error_safety_regression_text,
                kline_routes_regression_text,
                kline_collectors_regression_text,
                frontend_source_guard_text,
                "Frontend build",
                "local completion summary gate",
                "git_governance.status",
                "ready_for_live_orders_false",
                "pushed_to_origin",
                "codex/ai-agent-multitenant-foundation",
                "ai_trading_v1_live_stack_acceptance.py --confirm-local-mock-handoff",
                "Production evidence template remains blocked",
                explain_gate_text,
                "Production evidence initializer gate",
                "--init-production-evidence-file",
                "production_evidence_initializer_gate",
                prepared_initializer_gate_text,
                "real_order_backend_blocked",
                "Local LaunchAgent runtime sync",
                "scripts/local-dev/install_launch_agent.sh",
                "--require-runtime-mirror-current",
                "Runtime readiness attempt",
                "run_runtime_readiness_with_retry",
                runtime_readiness_retry_grace_runner_text,
                production_operator_preflight_runner_text,
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
                "Git：只在 `codex/ai-agent-multitenant-foundation` 分支开发；GitHub 上传已同步到 origin/codex/ai-agent-multitenant-foundation；不合并。",
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
                "Local V1 Production Operator Preflight Accepted / Remote Push Synced",
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
                "| AI Trading aggregate production evidence prepared initializer gate | Done |",
                "| AI Trading production evidence explain mode | Done |",
                "| AI Trading aggregate production evidence explain gate | Done |",
                admin_explain_api_marker,
                admin_evidence_ui_marker,
                admin_validation_api_marker,
                admin_validation_ui_marker,
                admin_template_api_marker,
                admin_template_ui_marker,
                admin_prepared_template_api_marker,
                admin_prepared_template_ui_marker,
                production_evidence_template_guidance_marker,
                production_evidence_validation_guidance_marker,
                production_evidence_root_guidance_marker,
                production_evidence_root_actions_marker,
                admin_payload_bounds_marker,
                production_evidence_summary_terms_marker,
                production_evidence_expiry_gate_marker,
                production_evidence_expiry_window_marker,
                production_evidence_cutover_approval_ref_marker,
                production_evidence_future_timestamp_guard_marker,
                production_evidence_validation_age_guard_marker,
                production_evidence_cutover_window_guard_marker,
                production_evidence_run_id_guard_marker,
                production_evidence_run_id_traceability_marker,
                production_evidence_item_artifact_traceability_marker,
                production_evidence_artifact_ref_uniqueness_marker,
                production_evidence_artifact_ref_item_uniqueness_marker,
                production_evidence_blocker_labels_marker,
                production_evidence_template_blocker_labels_marker,
                production_evidence_explain_root_blocker_labels_marker,
                production_evidence_progress_summary_marker,
                production_evidence_progress_actions_marker,
                production_evidence_progress_root_actions_marker,
                production_evidence_prepared_initializer_marker,
                production_evidence_dry_run_safety_metadata_marker,
                production_evidence_non_object_dry_run_safety_marker,
                production_evidence_frontend_error_safety_marker,
                admin_ai_runtime_last_error_redaction_marker,
                ai_stream_polling_error_redaction_marker,
                frontend_ai_stream_polling_error_safety_marker,
                frontend_ai_runtime_error_safety_marker,
                frontend_production_readiness_error_safety_marker,
                frontend_strategy_action_error_safety_marker,
                frontend_backtest_metrics_json_error_safety_marker,
                frontend_backtest_summary_inline_no_prompt_marker,
                frontend_program_backtest_inline_no_prompt_marker,
                frontend_program_backtest_run_inline_confirm_marker,
                frontend_signal_handoff_inline_confirm_marker,
                frontend_agent_session_archive_inline_confirm_marker,
                hyperliquid_wallet_delete_inline_confirm_marker,
                binance_wallet_delete_inline_confirm_marker,
                frontend_prompt_packet_sanitizer_marker,
                frontend_handoff_error_safety_marker,
                frontend_agent_session_error_safety_marker,
                local_supervisor_fork_resilience_marker,
                env_check_docker_probe_fallback_marker,
                local_acceptance_transient_retry_status_marker,
                agent_session_response_context_redaction_marker,
                frontend_session_context_prompt_sanitizer_marker,
                model_adjust_untrusted_context_boundary_marker,
                model_adjust_output_sanitizer_marker,
                frontend_model_adjust_output_safety_marker,
                model_gateway_exception_type_safety_marker,
                route_exception_detail_safety_marker,
                hyper_ai_tool_error_safety_marker,
                hyper_ai_service_stream_error_safety_marker,
                hyper_ai_memory_error_safety_marker,
                hyper_ai_memory_prompt_safety_marker,
                hyper_ai_memory_storage_safety_marker,
                hyper_ai_profile_safety_marker,
                hyper_ai_suggestions_context_safety_marker,
                hyper_ai_suggestions_output_safety_marker,
                hyper_ai_llm_base_url_safety_marker,
                hyper_ai_preset_endpoint_override_guard_marker,
                hyper_ai_custom_endpoint_ssrf_guard_marker,
                hyper_ai_llm_redirect_guard_marker,
                shared_ai_llm_redirect_guard_marker,
                shared_ai_llm_tls_verification_guard_marker,
                account_llm_connection_error_safety_marker,
                account_hyperliquid_builder_error_safety_marker,
                hyperliquid_wallet_error_safety_marker,
                hyperliquid_agent_wallet_error_safety_marker,
                hyperliquid_auxiliary_error_safety_marker,
                hyperliquid_core_route_error_safety_marker,
                hyperliquid_execution_route_error_safety_marker,
                hyperliquid_read_route_error_safety_marker,
                model_readiness_sensitive_endpoint_gate_marker,
                context_compression_error_safety_marker,
                context_compression_prompt_safety_marker,
                frontend_validation_warning_labels_marker,
                model_readiness_ui_source_guard_marker,
                model_readiness_next_actions_marker,
                model_setup_shortcut_marker,
                model_setup_runtime_refresh_marker,
                frontend_model_config_error_safety_marker,
                frontend_onboarding_error_safety_marker,
                frontend_onboarding_blank_page_guard_marker,
                frontend_model_config_nonblocking_entry_marker,
                frontend_main_page_api_key_config_entry_marker,
                frontend_onboarding_api_key_deferral_marker,
                frontend_public_asset_path_guard_marker,
                frontend_bot_tool_config_error_safety_marker,
                frontend_market_universe_error_safety_marker,
                frontend_market_symbol_sanitizer_marker,
                kline_local_db_api_marker,
                kline_collector_safety_marker,
                kline_maintenance_endpoint_safety_marker,
                private_factor_per_user_result_schema_marker,
                private_factor_precompute_writer_reader_marker,
                private_factor_precompute_db_smoke_marker,
                agent_session_id_safety_marker,
                agent_session_id_validation_error_safety_marker,
                agent_session_name_safety_marker,
                strategy_spec_name_safety_marker,
                handoff_error_message_safety_marker,
                handoff_confirmation_source_safety_marker,
                signal_rejection_reason_safety_marker,
                backtest_evidence_safety_marker,
                market_context_safety_marker,
                strategy_text_source_safety_marker,
                gateway_mode_guard_marker,
                "| AI Trading runtime mirror freshness gate | Done |",
                "| AI Trading runtime readiness cold-start retry | Done |",
                runtime_readiness_retry_grace_status_marker,
                "| AI Trading agent-session manual context secret rejection | Done |",
                "| AI Trading env-check runtime context budget gate | Done |",
                "| AI Trading runtime budget UI source guard | Done |",
                "| AI Trading completion audit git governance gate | Done |",
                "| AI Trading local completion summary gate | Done |",
                production_operator_preflight_status_marker,
                production_operator_preflight_dirty_tree_status_marker,
                production_operator_preflight_output_redaction_status_marker,
                production_url_host_secret_redaction_status_marker,
                production_url_port_safety_status_marker,
                production_url_parse_error_safety_status_marker,
                "| Remote push | Done | Branch pushed to origin/codex/ai-agent-multitenant-foundation; no merge performed |",
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
                "GitHub 上传：已同步到 origin/codex/ai-agent-multitenant-foundation",
                "codex/ai-agent-multitenant-foundation",
                "已 push，不 merge",
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
    generated_at: object = _UNSET,
    evidence_run_id: object = "ops-20260610-cutover-001",
    expires_at: object = _UNSET,
    cutover_window: object = _UNSET,
    cutover_approval_ref: object = _UNSET,
    validated_at: object = _UNSET,
    validated_by: object = "ops-admin",
    evidence_summary: object | None = None,
    root_extra: dict[str, object] | None = None,
    item_extra: dict[str, object] | None = None,
) -> None:
    if generated_at is _UNSET:
        generated_at = _utc_iso(timedelta(minutes=-2))
    if expires_at is _UNSET:
        expires_at = _utc_iso(timedelta(days=1))
    if validated_at is _UNSET:
        validated_at = _utc_iso(timedelta(minutes=-5))
    if cutover_window is _UNSET:
        cutover_window = {
            "start_at": _utc_iso(timedelta(minutes=-10)),
            "end_at": _utc_iso(timedelta(hours=2)),
        }
    evidence_run_id_for_refs = evidence_run_id if isinstance(evidence_run_id, str) and evidence_run_id else "ops-unknown-run"
    if cutover_approval_ref is _UNSET:
        cutover_approval_ref = f"ops://ai-trading/{evidence_run_id_for_refs}/production-cutover/approval"

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
                else _default_evidence_summary(requirement.id)
            ),
            "artifact_refs": (
                []
                if empty_artifact_refs
                else [artifact_ref_override or f"ops://ai-trading/{evidence_run_id_for_refs}/{requirement.id}/acceptance"]
            ),
            "secret_values_returned": False,
        }
        if item_extra:
            items[requirement.id].update(item_extra)
    payload = {
        "version": completion_audit.EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION,
        "evidence_run_id": evidence_run_id,
        "generated_at": generated_at,
        "expires_at": expires_at,
        "cutover_window": cutover_window,
        "cutover_approval_ref": cutover_approval_ref,
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
    report = completion_audit.build_completion_report(REPO_ROOT)

    assert report["local_v1_accepted"] is True
    assert report["ready_for_live_orders"] is False
    assert report["github_upload"] == "pushed_to_origin"
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


def test_private_factor_per_user_result_schema_is_declared() -> None:
    models_source = (REPO_ROOT / "backend" / "database" / "models.py").read_text(encoding="utf-8")
    migration_source = (
        REPO_ROOT / "backend" / "database" / "migrations" / "create_user_factor_result_tables.py"
    ).read_text(encoding="utf-8")
    migration_manager_source = (
        REPO_ROOT / "backend" / "database" / "migration_manager.py"
    ).read_text(encoding="utf-8")

    assert "class UserFactorValue(Base)" in models_source
    assert "__tablename__ = \"user_factor_values\"" in models_source
    assert "class UserFactorEffectiveness(Base)" in models_source
    assert "__tablename__ = \"user_factor_effectiveness\"" in models_source
    assert "ForeignKey(\"users.id\")" in models_source
    assert "ForeignKey(\"custom_factors.id\")" in models_source
    assert "'user_id', 'custom_factor_id', 'exchange', 'symbol', 'period', 'timestamp'" in models_source
    assert (
        "'user_id', 'custom_factor_id', 'exchange', 'symbol', 'period', 'forward_period', 'calc_date'"
        in models_source
    )

    assert "CREATE TABLE user_factor_values" in migration_source
    assert "CREATE TABLE user_factor_effectiveness" in migration_source
    assert "user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE" in migration_source
    assert "custom_factor_id INTEGER NOT NULL REFERENCES custom_factors(id) ON DELETE CASCADE" in migration_source
    assert "UNIQUE (user_id, custom_factor_id, exchange, symbol, period, timestamp)" in migration_source
    assert "user_id, custom_factor_id, exchange, symbol," in migration_source
    assert "period, forward_period, calc_date" in migration_source

    assert "\"create_user_factor_result_tables.py\"" in migration_manager_source
    assert (
        migration_manager_source.index("\"create_custom_factors_table.py\"")
        < migration_manager_source.index("\"add_custom_factor_user_scope.py\"")
        < migration_manager_source.index("\"create_user_factor_result_tables.py\"")
    )


def test_private_factor_precompute_writer_reader_uses_user_scoped_tables() -> None:
    effectiveness_source = (
        REPO_ROOT / "backend" / "services" / "factor_effectiveness_service.py"
    ).read_text(encoding="utf-8")
    resolver_source = (
        REPO_ROOT / "backend" / "services" / "factor_resolver.py"
    ).read_text(encoding="utf-8")
    tools_source = (
        REPO_ROOT / "backend" / "services" / "hyper_ai_tools.py"
    ).read_text(encoding="utf-8")
    smoke_source = (
        REPO_ROOT / "backend" / "scripts" / "ai_trading_private_factor_precompute_smoke.py"
    ).read_text(encoding="utf-8")
    status_source = (
        REPO_ROOT / "docs" / "hyperalpha" / "status" / "ai-agent-multitenant-foundation.status.md"
    ).read_text(encoding="utf-8")

    assert "def _upsert_user_factor_value" in effectiveness_source
    assert "INSERT INTO user_factor_values" in effectiveness_source
    assert "ON CONFLICT (user_id, custom_factor_id, exchange, symbol, period, timestamp)" in effectiveness_source
    assert "def _upsert_user_effectiveness" in effectiveness_source
    assert "INSERT INTO user_factor_effectiveness" in effectiveness_source
    assert (
        "ON CONFLICT (user_id, custom_factor_id, exchange, symbol, period, forward_period, calc_date)"
        in effectiveness_source
    )
    assert "private_user_id = int(custom_factor.user_id)" in effectiveness_source
    assert "user_id=private_user_id" in effectiveness_source
    assert "CustomFactor.user_id == None" in effectiveness_source

    assert "and_(\n                CustomFactor.source == \"builtin_expression\"" in resolver_source
    assert "\"user_id\": custom.user_id" in resolver_source

    assert "resolve_factor_definition(db, factor_name, user_id=user_id)" in tools_source
    assert "FROM user_factor_effectiveness" in tools_source
    assert "FROM user_factor_values" in tools_source
    assert "\"storage_scope\": storage_scope" in tools_source
    assert "\"source\": \"user_private\"" in tools_source

    assert "FactorEffectivenessService()" in smoke_source
    assert "service._get_symbols = lambda db, exchange: [SYMBOL]" in smoke_source
    assert "execute_query_factors(" in smoke_source
    assert "same_private_factor" in smoke_source
    assert "shared_table_rows" in smoke_source
    assert "factor_effectiveness" in smoke_source
    assert "factor_values" in smoke_source
    assert "_cleanup(db, run_id)" in smoke_source

    assert "| AI Trading private factor precompute writer-reader | Done |" in status_source
    assert "| AI Trading private factor precompute DB smoke | Done |" in status_source


def test_agent_session_id_safety_is_implemented_and_gated() -> None:
    service_source = (
        REPO_ROOT / "backend" / "services" / "ai_trading_strategy_spec_service.py"
    ).read_text(encoding="utf-8")
    route_source = (
        REPO_ROOT / "backend" / "api" / "ai_trading_routes.py"
    ).read_text(encoding="utf-8")
    route_test_source = (
        REPO_ROOT / "backend" / "tests" / "test_ai_trading_routes.py"
    ).read_text(encoding="utf-8")
    frontend_test_source = (
        REPO_ROOT / "backend" / "tests" / "test_ai_trading_frontend_readiness_source.py"
    ).read_text(encoding="utf-8")
    status_source = (
        REPO_ROOT / "docs" / "hyperalpha" / "status" / "ai-agent-multitenant-foundation.status.md"
    ).read_text(encoding="utf-8")

    assert "def _clean_agent_session_id" in service_source
    assert "SENSITIVE_AI_TRADING_KEY_PATTERN.search(raw)" in service_source
    assert "agent_session_id must not contain API keys" in service_source
    assert "except ValueError as exc" in route_source
    assert "list_strategy_spec_records(" in route_source
    assert "list_signal_event_records(" in route_source
    assert "test_ai_trading_agent_session_id_rejects_sensitive_values_without_echo" in route_test_source
    assert "test_hyper_ai_agent_session_route_id_rejects_sensitive_values_source_guard" in frontend_test_source
    assert "| AI Trading agent-session id safety | Done |" in status_source


def test_agent_session_id_validation_error_safety_is_implemented_and_gated() -> None:
    service_source = (
        REPO_ROOT / "backend" / "services" / "ai_trading_strategy_spec_service.py"
    ).read_text(encoding="utf-8")
    route_source = (
        REPO_ROOT / "backend" / "api" / "ai_trading_routes.py"
    ).read_text(encoding="utf-8")
    route_test_source = (
        REPO_ROOT / "backend" / "tests" / "test_ai_trading_routes.py"
    ).read_text(encoding="utf-8")
    status_source = (
        REPO_ROOT / "docs" / "hyperalpha" / "status" / "ai-agent-multitenant-foundation.status.md"
    ).read_text(encoding="utf-8")

    assert "if len(raw) > 80:" in service_source
    assert "raw = raw[:80]" not in service_source
    assert "agent_session_id: Optional[str] = None" in route_source
    assert "agent_session_id: str = Path(...)" in route_source
    assert "agent_session_id: Optional[str] = Query(default=None)" in route_source
    assert "agent_session_id: Optional[str] = Field(" not in route_source
    assert "agent_session_id_rejects_sensitive_values_without_echo" in route_test_source
    assert "session:api_key=secret-validation-echo" in route_test_source
    assert "too_long_session_id" in route_test_source
    assert "| AI Trading agent-session id validation error safety | Done |" in status_source


def test_kline_local_db_api_is_implemented_and_gated() -> None:
    route_source = (
        REPO_ROOT / "backend" / "api" / "kline_routes.py"
    ).read_text(encoding="utf-8")
    runner_source = (
        REPO_ROOT / "scripts" / "local-dev" / "run_ai_trading_v1_local_acceptance.sh"
    ).read_text(encoding="utf-8")
    status_source = (
        REPO_ROOT / "docs" / "hyperalpha" / "status" / "ai-agent-multitenant-foundation.status.md"
    ).read_text(encoding="utf-8")

    assert "K-line data service not implemented yet" not in route_source
    assert "CryptoKline" in route_source
    assert "\"source\": \"local_db\"" in route_source
    assert "_resolve_exchange(db, current_user, exchange)" in route_source
    assert "CryptoKline.symbol.in_(symbol_candidates)" in route_source
    assert "Invalid symbol" in route_source
    assert "Unsupported period" in route_source
    assert "Failed to get K-line data for local DB request: {type(e).__name__}" in route_source
    assert "tests/test_kline_routes.py" in runner_source
    assert "| AI Trading K-line local DB API | Done |" in status_source


def test_kline_collector_and_backfill_safety_are_implemented_and_gated() -> None:
    collector_source = (
        REPO_ROOT / "backend" / "services" / "kline_collectors.py"
    ).read_text(encoding="utf-8")
    backfill_source = (
        REPO_ROOT / "backend" / "services" / "kline_backfill_manager.py"
    ).read_text(encoding="utf-8")
    route_source = (
        REPO_ROOT / "backend" / "api" / "kline_routes.py"
    ).read_text(encoding="utf-8")
    runner_source = (
        REPO_ROOT / "scripts" / "local-dev" / "run_ai_trading_v1_local_acceptance.sh"
    ).read_text(encoding="utf-8")
    status_source = (
        REPO_ROOT / "docs" / "hyperalpha" / "status" / "ai-agent-multitenant-foundation.status.md"
    ).read_text(encoding="utf-8")

    assert "_normalize_kline_payload" in collector_source
    assert '("timestamp", "t", "time")' in collector_source
    assert '("open", "o")' in collector_source
    assert "klines[-1]" in collector_source
    assert "Skipping malformed Hyperliquid kline payload" in collector_source
    assert "SAFE_BACKFILL_ERROR_MESSAGE = \"K-line backfill failed\"" in backfill_source
    assert "task.error_message = SAFE_BACKFILL_ERROR_MESSAGE" in backfill_source
    assert "Unsupported exchange" in route_source
    assert "_normalize_request_symbol(symbol)" in route_source
    assert "A backfill task is already running. Please wait for it to complete." in route_source
    assert "tests/test_kline_collectors.py" in runner_source
    assert "| AI Trading K-line collector/backfill safety | Done |" in status_source


def test_kline_maintenance_endpoint_safety_is_implemented_and_gated() -> None:
    route_source = (
        REPO_ROOT / "backend" / "api" / "kline_routes.py"
    ).read_text(encoding="utf-8")
    test_source = (
        REPO_ROOT / "backend" / "tests" / "test_kline_routes.py"
    ).read_text(encoding="utf-8")
    status_source = (
        REPO_ROOT / "docs" / "hyperalpha" / "status" / "ai-agent-multitenant-foundation.status.md"
    ).read_text(encoding="utf-8")

    assert 'detail="Failed to delete task"' in route_source
    assert 'detail="Failed to detect gaps"' in route_source
    assert 'detail="Failed to get supported symbols"' in route_source
    assert "days: int = Query(7, ge=1, le=30)" in route_source
    assert "normalized_symbol = _normalize_request_symbol(symbol)" in route_source
    assert "symbol.upper()" not in route_source
    assert "test_delete_backfill_task_uses_fixed_error_label" in test_source
    assert "test_detect_gaps_validates_symbol_and_uses_fixed_error_label" in test_source
    assert "test_supported_symbols_uses_fixed_error_label" in test_source
    assert "| AI Trading K-line maintenance endpoint safety | Done |" in status_source


def test_production_evidence_template_builder_uses_required_item_ids_without_secrets():
    payload = completion_audit.build_external_acceptance_evidence_template()

    assert payload["version"] == completion_audit.EXTERNAL_ACCEPTANCE_EVIDENCE_VERSION
    assert payload["evidence_run_id"] is None
    assert payload["generated_at"] is None
    assert payload["expires_at"] is None
    assert payload["cutover_window"] == {"start_at": None, "end_at": None}
    assert payload["cutover_approval_ref"] is None
    assert payload["secret_values_returned"] is False
    assert any("required non-secret proof terms" in note for note in payload["notes"])
    assert all(len(note) <= completion_audit.MAX_PRODUCTION_EVIDENCE_NOTE_CHARS for note in payload["notes"])
    assert set(payload["items"]) == {requirement.id for requirement in completion_audit.EXTERNAL_REQUIREMENTS}
    assert all(item["status"] == "pending_external_acceptance" for item in payload["items"].values())
    assert all(item["secret_values_returned"] is False for item in payload["items"].values())
    assert completion_audit._secret_pattern_hits(payload) == []


def test_production_evidence_template_guidance_uses_required_item_ids_without_secrets():
    guidance = completion_audit.build_external_acceptance_evidence_template_guidance()

    assert guidance["secret_policy"] == "metadata_only_no_env_or_credentials"
    assert any(
        field["field"] == "evidence_run_id"
        and "external_evidence_run_id_missing" in field["related_blockers"]
        for field in guidance["root_fields"]
    )
    assert any(
        field["field"] == "cutover_window"
        and "external_evidence_cutover_window_ended" in field["related_blockers"]
        for field in guidance["root_fields"]
    )
    assert any(
        action.startswith("root.evidence_run_id:")
        and "cutover_approval_ref" in action
        for action in guidance["root_next_required_actions"]
    )
    assert any(
        action.startswith("root.secret_values_returned:")
        for action in guidance["root_next_required_actions"]
    )
    assert len(guidance["items"]) == len(completion_audit.EXTERNAL_REQUIREMENTS)
    assert len(guidance["next_required_actions"]) == len(completion_audit.EXTERNAL_REQUIREMENTS)
    order_backend_item = next(item for item in guidance["items"] if item["id"] == "real_order_backend_handoff")
    assert "mode=http / gateway mode=http / gateway_mode=http" in order_backend_item["required_summary_terms"]
    assert any("real HTTPS order-backend" in action for action in order_backend_item["operator_guidance"])
    assert "bearer tokens" in order_backend_item["forbidden_values"]
    assert "ops" in order_backend_item["safe_artifact_ref_schemes"]
    assert completion_audit._secret_pattern_hits(guidance) == []


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
    assert (
        "generated_at=timezone-aware ISO-8601 timestamp not more than 300 seconds in the future"
        in report["schema"]["required_root_fields"]
    )
    assert (
        "evidence_run_id=safe unique run id, 12-80 chars, letters/numbers/._:- only, referenced by cutover_approval_ref and item artifact_refs"
        in report["schema"]["required_root_fields"]
    )
    assert (
        "expires_at=timezone-aware ISO-8601 timestamp after generated_at, in the future, and within 7 days"
        in report["schema"]["required_root_fields"]
    )
    assert (
        "cutover_window=start_at/end_at timezone-aware ISO-8601 window containing the production audit time and no longer than 8 hours"
        in report["schema"]["required_root_fields"]
    )
    assert (
        "cutover_approval_ref=1 safe ops/lark/notion/https approval ref for the live-order cutover"
        in report["schema"]["required_root_fields"]
    )
    assert report["schema"]["max_clock_skew_seconds"] == 300
    assert report["schema"]["max_item_validation_age_days"] == 7
    assert report["schema"]["max_cutover_window_hours"] == 8
    assert report["schema"]["min_evidence_run_id_chars"] == 12
    assert report["schema"]["max_evidence_run_id_chars"] == 80
    assert "status=accepted" in report["schema"]["required_item_fields"]
    assert (
        "validated_at=timezone-aware ISO-8601 timestamp not more than 300 seconds in the future and not older than 7 days at generated_at"
        in report["schema"]["required_item_fields"]
    )
    order_backend_item = next(
        item for item in report["items"] if item["id"] == "real_order_backend_handoff"
    )
    assert report["progress"]["next_required_actions"][0].startswith(
        "macos_reboot_recovery: After a real macOS reboot"
    )
    assert any(
        action.startswith("root.evidence_run_id:")
        for action in report["progress"]["root_next_required_actions"]
    )
    assert any(
        action.startswith("root.cutover_window:")
        for action in report["progress"]["root_next_required_actions"]
    )
    assert any(
        action.startswith("real_order_backend_handoff: Configure the real HTTPS order-backend")
        for action in report["progress"]["next_required_actions"]
    )
    assert order_backend_item["ready"] is False
    assert "external_evidence_item_not_provided" in order_backend_item["blockers"]
    assert "API keys" in order_backend_item["forbidden_values"]
    assert "HTTPS" in order_backend_item["required_summary_terms"]
    assert "mode=http / gateway mode=http / gateway_mode=http" in order_backend_item["required_summary_terms"]
    assert "Configure the real HTTPS order-backend signal gateway" in order_backend_item["operator_guidance"][0]


def test_production_evidence_payload_validation_handles_non_object_without_secret_echo(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)

    report = completion_audit.build_production_evidence_payload_validation(
        tmp_path,
        "Authorization: Bearer secret-production-token-123456789",
    )

    assert report["mode"] == "production_evidence_payload_validation"
    assert report["ready_for_live_orders"] is False
    assert report["production_evidence"]["ready"] is False
    assert report["production_evidence"]["path"] is None
    assert report["production_evidence"]["secret_pattern_count"] >= 1
    assert "external_evidence_root_must_be_object" in report["production_evidence"]["blockers"]
    assert "external_evidence_secret_pattern_detected" in report["production_evidence"]["blockers"]
    assert report["progress"]["root_next_required_actions"][0].startswith("root.schema:")
    serialized = json.dumps(report, ensure_ascii=False)
    assert "secret-production-token-123456789" not in serialized
    assert "Authorization: Bearer" not in serialized


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
    assert report["progress"]["next_required_actions"] == []
    assert report["progress"]["root_next_required_actions"] == []
    assert all(item["ready"] is True for item in report["items"])
    assert all(item["blockers"] == [] for item in report["items"])


def test_production_evidence_explain_cli_outputs_non_secret_checklist(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)

    completed = _run_subprocess_with_transient_retry(
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
    assert payload["github_upload"] == "pushed_to_origin"
    assert payload["production_evidence"]["ready"] is False
    assert "bearer tokens" in payload["items"][0]["forbidden_values"]
    assert completion_audit._secret_pattern_hits(payload) == []


def test_production_evidence_prepare_cli_outputs_pending_prefilled_packet(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    output_path = _outside_repo_evidence_path(tmp_path, "prepared-cli-production-evidence.json")
    run_id = "prod:20260612T040506Z"

    completed = _run_subprocess_with_transient_retry(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--repo-root",
            str(tmp_path),
            "--prepare-production-evidence-file",
            str(output_path),
            "--production-evidence-run-id",
            run_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    prepared = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["created"] is True
    assert payload["evidence_run_id"] == run_id
    assert payload["production_evidence_ready"] is False
    assert payload["production_evidence_accepted_count"] == 0
    assert payload["production_evidence_root_blockers"] == []
    assert prepared["evidence_run_id"] == run_id
    assert all(run_id in item["artifact_refs"][0] for item in prepared["items"].values())
    assert completion_audit._secret_pattern_hits(payload) == []
    assert completion_audit._secret_pattern_hits(prepared) == []


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
    assert "external_evidence_run_id_missing" in completion_report["production_evidence"]["blockers"]
    assert "external_evidence_generated_at_missing" in completion_report["production_evidence"]["blockers"]
    assert "external_evidence_expires_at_missing" in completion_report["production_evidence"]["blockers"]
    assert "external_evidence_cutover_approval_ref_missing" in completion_report["production_evidence"]["blockers"]
    assert "external_evidence_item_blocked:real_order_backend_handoff" in completion_report["production_evidence"]["blockers"]


def test_production_evidence_prepared_initializer_prefills_safe_pending_packet(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    output_path = _outside_repo_evidence_path(tmp_path, "prepared-production-evidence.json")
    run_id = "prod:20260612T010203Z"

    prepared_report = completion_audit.write_prepared_external_acceptance_evidence_template(
        output_path,
        repo_root=tmp_path,
        evidence_run_id=run_id,
        cutover_window_hours=2,
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    completion_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=output_path,
        allow_live_ready_from_evidence=True,
    )

    assert prepared_report["created"] is True
    assert prepared_report["ready_for_live_orders"] is False
    assert prepared_report["production_evidence_ready"] is False
    assert prepared_report["production_evidence_accepted_count"] == 0
    assert prepared_report["production_evidence_root_blockers"] == []
    assert prepared_report["evidence_run_id"] == run_id
    assert payload["evidence_run_id"] == run_id
    assert payload["generated_at"]
    assert payload["expires_at"]
    assert payload["cutover_window"]["start_at"]
    assert payload["cutover_window"]["end_at"]
    assert run_id in payload["cutover_approval_ref"]
    assert payload["secret_values_returned"] is False
    assert all(item["status"] == "pending_external_acceptance" for item in payload["items"].values())
    assert all(item["secret_values_returned"] is False for item in payload["items"].values())
    assert all(run_id in item["artifact_refs"][0] for item in payload["items"].values())
    assert all(item_id in item["artifact_refs"][0] for item_id, item in payload["items"].items())

    evidence = completion_report["production_evidence"]
    assert completion_report["ready_for_live_orders"] is False
    assert evidence["provided"] is True
    assert evidence["file_inside_repo"] is False
    assert evidence["evidence_run_id_present"] is True
    assert evidence["cutover_window_present"] is True
    assert evidence["cutover_approval_ref_present"] is True
    assert evidence["accepted_count"] == 0
    assert "external_evidence_run_id_missing" not in evidence["blockers"]
    assert "external_evidence_generated_at_missing" not in evidence["blockers"]
    assert "external_evidence_expires_at_missing" not in evidence["blockers"]
    assert "external_evidence_cutover_approval_ref_missing" not in evidence["blockers"]
    assert "external_evidence_cutover_window_start_at_missing" not in evidence["blockers"]
    assert "external_evidence_artifact_ref_missing_run_id" not in str(evidence["items"])
    assert "external_evidence_artifact_ref_missing_item_id" not in str(evidence["items"])
    assert "external_evidence_item_blocked:real_order_backend_handoff" in evidence["blockers"]
    assert completion_audit._secret_pattern_hits(payload) == []


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


def test_production_evidence_prepared_initializer_refuses_bad_run_id(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    output_path = _outside_repo_evidence_path(tmp_path, "bad-run-id-production-evidence.json")

    prepared_report = completion_audit.write_prepared_external_acceptance_evidence_template(
        output_path,
        repo_root=tmp_path,
        evidence_run_id="api_key=secret",
    )

    assert prepared_report["created"] is False
    assert not output_path.exists()
    assert "external_evidence_run_id_invalid_chars" in prepared_report["blockers"]
    assert "external_evidence_run_id_secret_pattern_detected" in prepared_report["blockers"]


def test_completion_audit_blocks_local_acceptance_when_db_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_db_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Default production readiness DB-audit gate remains blocked" in runner_evidence["missing_phrases"]
    assert "--include-db-audits" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_local_dev_shell_syntax_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_local_dev_shell_syntax_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Local dev shell syntax" in runner_evidence["missing_phrases"]


def test_local_acceptance_runner_retries_transient_resource_failures_without_masking_contract_errors():
    runner_source = RUNNER_SCRIPT_PATH.read_text(encoding="utf-8")

    expected_failure_start = runner_source.index("run_expected_failure()")
    transient_guard_index = runner_source.index(
        'if is_transient_resource_failure "$rc" "$output_file"; then',
        expected_failure_start,
    )
    expected_blocker_index = runner_source.index('if [[ "$rc" -eq 1 ]]; then', expected_failure_start)

    assert "run_command_with_transient_retry" in runner_source
    assert "output_contains_transient_resource_failure" in runner_source
    assert "sleep_before_retry" in runner_source
    assert "Retry sleep could not start under local resource pressure" in runner_source
    assert "AI_TRADING_TRANSIENT_RETRY_ATTEMPTS" in runner_source
    assert "AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS" in runner_source
    assert "Transient local resource failure" in runner_source
    assert "Resource temporarily unavailable" in runner_source
    assert "Failed to spawn" in runner_source
    assert "fork failed" in runner_source
    assert '"$rc" -eq 2 || "$rc" -eq 128' not in runner_source
    assert '[[ "$rc" -ne 0 ]] || return 1' in runner_source
    assert transient_guard_index < expected_blocker_index
    assert "refusing to treat it as the expected blocker" in runner_source
    assert 'if [[ "$rc" -eq 1 ]]; then' in runner_source
    assert "Expected blocker confirmed with exit status 1" in runner_source
    assert "Expected exit status 1, got $rc" in runner_source


def test_local_acceptance_expected_failure_gate_retries_rc1_resource_pressure_before_accepting_blocker(tmp_path):
    counter_path = tmp_path / "flaky-counter"
    shell_script = f"""
set -euo pipefail
{_runner_function_source()}
counter_path={counter_path.as_posix()!r}
printf '0' > "$counter_path"
flaky_expected_gate() {{
  local current
  current="$(cat "$counter_path")"
  if [[ "$current" -eq 0 ]]; then
    printf '1' > "$counter_path"
    echo "fork: Resource temporarily unavailable"
    return 1
  fi
  echo "default production blocker"
  return 1
}}
AI_TRADING_TRANSIENT_RETRY_ATTEMPTS=2 \\
AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS=1 \\
  run_expected_failure "Simulated expected failure gate" flaky_expected_gate
[[ "$(cat "$counter_path")" == "1" ]]
"""

    result = _run_bash_script_with_transient_retry(shell_script)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Transient local resource failure during Simulated expected failure gate" in result.stderr
    assert "Expected blocker confirmed with exit status 1" in result.stdout


def test_local_acceptance_transient_resource_detection_is_not_exit_code_whitelisted(tmp_path):
    output_path = tmp_path / "fork-pressure.log"
    shell_script = f"""
set -euo pipefail
{_runner_function_source()}
output_path={output_path.as_posix()!r}
printf '%s\\n' "bash: fork: Resource temporarily unavailable" > "$output_path"
is_transient_resource_failure 1 "$output_path"
is_transient_resource_failure 254 "$output_path"
if is_transient_resource_failure 0 "$output_path"; then
  exit 10
fi
printf '%s\\n' "regular contract failure" > "$output_path"
if is_transient_resource_failure 1 "$output_path"; then
  exit 11
fi
"""

    result = _run_bash_script_with_transient_retry(shell_script)

    assert result.returncode == 0, result.stdout + result.stderr


def test_local_acceptance_retry_sleep_failure_does_not_abort_runner(tmp_path):
    shell_script = f"""
set -euo pipefail
{_runner_function_source()}
sleep() {{
  echo "fork: Resource temporarily unavailable" >&2
  return 128
}}
sleep_before_retry 1
"""

    result = _run_bash_script_with_transient_retry(shell_script)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Retry sleep could not start under local resource pressure" in result.stderr


def test_local_acceptance_runner_uses_macos_portable_mktemp_templates():
    runner_source = RUNNER_SCRIPT_PATH.read_text(encoding="utf-8")

    assert ".XXXXXX.log" not in runner_source
    assert ".XXXXXX.json" not in runner_source
    assert "ai-trading-local-step.log.XXXXXX" in runner_source
    assert "ai-trading-local-expected-failure.log.XXXXXX" in runner_source
    assert "ai-trading-completion-audit.json.XXXXXX" in runner_source
    assert "ai-trading-production-evidence.json.XXXXXX" in runner_source
    assert "ai-trading-production-evidence-init.json.XXXXXX" in runner_source
    assert "ai-trading-production-evidence-audit.json.XXXXXX" in runner_source
    assert "ai-trading-production-evidence-explain.json.XXXXXX" in runner_source
    assert "ai-trading-production-operator-preflight.json.XXXXXX" in runner_source


def test_local_acceptance_runner_retries_temp_file_creation_under_resource_pressure():
    runner_source = _runner_function_source()

    assert "make_temp_file_with_retry()" in runner_source
    assert "Transient local resource failure while creating temp file" in runner_source
    assert "make_temp_file_with_retry output_file" in runner_source
    assert "make_temp_file_with_retry report_file" in runner_source
    assert "make_temp_file_with_retry evidence_file" in runner_source
    assert "make_temp_file_with_retry preflight_report_file" in runner_source


def test_completion_audit_blocks_local_acceptance_when_transient_retry_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_local_acceptance_transient_retry_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert "AI_TRADING_TRANSIENT_RETRY_ATTEMPTS" in runner_evidence["missing_phrases"]
    assert "AI_TRADING_TRANSIENT_RETRY_SLEEP_SECONDS" in runner_evidence["missing_phrases"]
    assert "Transient local resource failure" in runner_evidence["missing_phrases"]
    assert "run_command_with_transient_retry" in runner_evidence["missing_phrases"]
    assert "make_temp_file_with_retry" in runner_evidence["missing_phrases"]
    assert "| AI Trading local acceptance transient retry | Done |" in status_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_runtime_readiness_retry_grace_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_runtime_readiness_retry_grace_marker=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert "AI_TRADING_RUNTIME_READINESS_ATTEMPTS" in runner_evidence["missing_phrases"]
    assert "AI_TRADING_RUNTIME_READINESS_SLEEP_SECONDS" in runner_evidence["missing_phrases"]
    assert "Runtime readiness still blocked" in runner_evidence["missing_phrases"]
    assert "| AI Trading runtime readiness retry grace | Done |" in status_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_production_operator_preflight_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_production_operator_preflight_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert "Production operator preflight remains blocked" in runner_evidence["missing_phrases"]
    assert "ai_trading_v1_production_operator_preflight.py --skip-local-runtime --strict" in runner_evidence["missing_phrases"]
    assert "production_operator_preflight_gate" in runner_evidence["missing_phrases"]
    assert "completion:live_orders_not_ready" in runner_evidence["missing_phrases"]
    assert "| AI Trading production operator preflight | Done |" in status_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_production_preflight_dirty_tree_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_operator_preflight_dirty_tree_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert (
        "| AI Trading production operator preflight dirty-tree blocker | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_operator_preflight_output_redaction_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_operator_preflight_output_redaction_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert (
        "| AI Trading production operator preflight output redaction | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_url_host_secret_redaction_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_url_host_secret_redaction_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert (
        "| AI Trading production URL host secret redaction | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_url_port_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_url_port_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert (
        "| AI Trading production URL port safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_url_parse_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_url_parse_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert (
        "| AI Trading production URL parse-error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_source_guard_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_frontend_source_guard=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "tests/test_ai_trading_frontend_readiness_source.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_ai_stream_routes_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_ai_stream_routes_regression_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "tests/test_ai_stream_routes.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_kline_routes_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_kline_routes_regression_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    local_blockers = report["summary"]["local_blockers"]
    assert "aggregate_local_acceptance_runner" in local_blockers
    assert "status_progress_marker" in local_blockers
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert "tests/test_kline_routes.py" in runner_evidence["missing_phrases"]
    assert "| AI Trading K-line local DB API | Done |" in status_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_kline_collector_safety_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_kline_collector_safety_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    local_blockers = report["summary"]["local_blockers"]
    assert "aggregate_local_acceptance_runner" in local_blockers
    assert "status_progress_marker" in local_blockers
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert "tests/test_kline_collectors.py" in runner_evidence["missing_phrases"]
    assert "| AI Trading K-line collector/backfill safety | Done |" in status_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_kline_maintenance_endpoint_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_kline_maintenance_endpoint_safety_marker=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert "| AI Trading K-line maintenance endpoint safety | Done |" in status_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_explain_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_production_evidence_explain_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Production evidence explain mode gate" in runner_evidence["missing_phrases"]
    assert "--explain-production-evidence" in runner_evidence["missing_phrases"]
    assert "production_evidence_explain_gate" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_prepared_initializer_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(tmp_path, include_production_evidence_prepared_initializer_gate=False)

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert "Production evidence prepared initializer gate" in runner_evidence["missing_phrases"]
    assert "--prepare-production-evidence-file" in runner_evidence["missing_phrases"]
    assert "production_evidence_prepared_initializer_gate" in runner_evidence["missing_phrases"]


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


def test_completion_audit_blocks_local_acceptance_when_admin_prepared_template_api_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_prepared_template_api_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence prepared template API | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_prepared_template_ui_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_production_evidence_prepared_template_ui_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin production evidence prepared template UI | Done |"
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


def test_completion_audit_blocks_local_acceptance_when_production_evidence_summary_terms_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_summary_terms_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence summary terms | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_expiry_gate_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_expiry_gate_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence expiry gate | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_expiry_window_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_expiry_window_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence expiry window | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_cutover_approval_ref_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_cutover_approval_ref_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence cutover approval ref | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_future_timestamp_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_future_timestamp_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence future timestamp guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_validation_age_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_validation_age_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence validation age guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_cutover_window_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_cutover_window_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence cutover window guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_run_id_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_run_id_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence run id guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_run_id_traceability_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_run_id_traceability_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence run id traceability | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_item_artifact_traceability_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_item_artifact_traceability_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence item artifact traceability | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_artifact_ref_uniqueness_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_artifact_ref_uniqueness_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence artifact ref uniqueness | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_artifact_ref_item_uniqueness_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_artifact_ref_item_uniqueness_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence artifact ref item uniqueness | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_blocker_labels_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_blocker_labels_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence blocker labels | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_template_blocker_labels_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_template_blocker_labels_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence template blocker labels | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_explain_root_blocker_labels_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_explain_root_blocker_labels_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence explain root blocker labels | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_progress_summary_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_progress_summary_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence progress summary | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_progress_actions_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_progress_actions_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence progress actions | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_progress_root_actions_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_progress_root_actions_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence progress root actions | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_prepared_initializer_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_prepared_initializer_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence prepared initializer | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_dry_run_safety_metadata_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_dry_run_safety_metadata_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence dry-run safety metadata | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_non_object_dry_run_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_non_object_dry_run_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence non-object dry-run safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_frontend_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_frontend_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence frontend error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_admin_ai_runtime_last_error_redaction_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_admin_ai_runtime_last_error_redaction_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading admin AI runtime last-error redaction | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_ai_stream_polling_error_redaction_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_ai_stream_polling_error_redaction_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading AI stream polling error redaction | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_ai_stream_polling_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_ai_stream_polling_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend AI stream polling error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_ai_runtime_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_ai_runtime_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend AI runtime error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_production_readiness_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_production_readiness_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend production-readiness error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_handoff_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_handoff_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend handoff error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_strategy_action_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_strategy_action_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend strategy-action error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_backtest_metrics_json_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_backtest_metrics_json_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend backtest metrics JSON error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_backtest_summary_inline_no_prompt_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_backtest_summary_inline_no_prompt_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend backtest summary inline no-prompt | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_program_backtest_inline_no_prompt_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_program_backtest_inline_no_prompt_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend program backtest inline no-prompt | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_program_backtest_run_inline_confirm_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_program_backtest_run_inline_confirm_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend program backtest run inline confirm | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_signal_handoff_inline_confirm_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_signal_handoff_inline_confirm_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend signal handoff inline confirm | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_agent_session_archive_inline_confirm_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_agent_session_archive_inline_confirm_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend agent-session archive inline confirm | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_wallet_delete_inline_confirm_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_wallet_delete_inline_confirm_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid wallet delete inline confirm | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_binance_wallet_delete_inline_confirm_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_binance_wallet_delete_inline_confirm_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Binance wallet delete inline confirm | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_prompt_packet_sanitizer_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_prompt_packet_sanitizer_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend prompt-packet sanitizer | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_agent_session_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_agent_session_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend agent-session error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_local_supervisor_fork_resilience_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_local_supervisor_fork_resilience_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading local supervisor fork-pressure resilience | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_env_check_docker_probe_fallback_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_env_check_docker_probe_fallback_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading env-check Docker probe fallback | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_template_guidance_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_template_guidance_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence template guidance | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_validation_guidance_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_validation_guidance_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence validation guidance | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_root_guidance_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_root_guidance_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence root guidance | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_production_evidence_root_actions_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_production_evidence_root_actions_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading production evidence root actions | Done |"
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


def test_completion_audit_blocks_local_acceptance_when_model_gateway_exception_type_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_gateway_exception_type_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model/gateway exception type safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_route_exception_detail_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_route_exception_detail_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading route exception detail safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_tool_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_tool_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI tool error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_service_stream_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_service_stream_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI service stream error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_memory_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_memory_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI memory error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_memory_prompt_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_memory_prompt_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI memory prompt safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_memory_storage_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_memory_storage_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI memory storage safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_profile_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_profile_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI profile safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_suggestions_context_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_suggestions_context_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI suggestions context safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_suggestions_output_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_suggestions_output_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI suggestions output safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_llm_base_url_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_llm_base_url_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI LLM base URL safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_preset_endpoint_override_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_preset_endpoint_override_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI preset endpoint override guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_custom_endpoint_ssrf_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_custom_endpoint_ssrf_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI custom endpoint SSRF guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyper_ai_llm_redirect_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyper_ai_llm_redirect_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyper AI LLM redirect guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_shared_ai_llm_redirect_guard_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_shared_ai_llm_redirect_guard_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_shared_ai_llm_redirect_guard.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_shared_ai_llm_redirect_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_shared_ai_llm_redirect_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading shared AI LLM redirect guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_shared_ai_llm_tls_verification_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_shared_ai_llm_tls_verification_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading shared AI LLM TLS verification guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_account_llm_connection_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_account_llm_connection_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_account_llm_connection_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_account_llm_connection_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_account_llm_connection_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading account LLM connection error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_account_hyperliquid_builder_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_account_hyperliquid_builder_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_account_hyperliquid_builder_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_account_hyperliquid_builder_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_account_hyperliquid_builder_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading account Hyperliquid builder error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_wallet_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_wallet_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_hyperliquid_wallet_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_wallet_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_wallet_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid private-key wallet error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_agent_wallet_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_agent_wallet_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_hyperliquid_agent_wallet_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_agent_wallet_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_agent_wallet_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid agent-wallet error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_auxiliary_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_auxiliary_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_hyperliquid_auxiliary_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_auxiliary_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_auxiliary_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid auxiliary route error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_core_route_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_core_route_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_hyperliquid_core_route_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_core_route_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_core_route_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid core route error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_execution_route_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_execution_route_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_hyperliquid_execution_route_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_execution_route_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_execution_route_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid execution route error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_read_route_error_safety_regression_gate_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_read_route_error_safety_regression_gate=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "aggregate_local_acceptance_runner" in report["summary"]["local_blockers"]
    runner_evidence = next(item for item in report["local_evidence"] if item["id"] == "aggregate_local_acceptance_runner")
    assert runner_evidence["status"] == "incomplete_evidence"
    assert "tests/test_hyperliquid_read_route_error_safety.py" in runner_evidence["missing_phrases"]


def test_completion_audit_blocks_local_acceptance_when_hyperliquid_read_route_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_hyperliquid_read_route_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading Hyperliquid read route error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_model_readiness_sensitive_endpoint_gate_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_readiness_sensitive_endpoint_gate_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model readiness sensitive endpoint gate | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_context_compression_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_context_compression_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading context compression error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_context_compression_prompt_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_context_compression_prompt_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading context compression prompt safety | Done |"
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


def test_completion_audit_blocks_local_acceptance_when_model_readiness_ui_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_readiness_ui_source_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model readiness UI source guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_model_readiness_next_actions_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_readiness_next_actions_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model readiness next actions | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_model_setup_shortcut_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_setup_shortcut_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model setup shortcut | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_model_setup_runtime_refresh_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_model_setup_runtime_refresh_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading model setup runtime refresh | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_model_config_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_model_config_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend model-config error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_onboarding_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_onboarding_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend onboarding error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_onboarding_blank_page_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_onboarding_blank_page_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend onboarding blank-page guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_model_config_nonblocking_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_model_config_nonblocking_entry_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend model-config nonblocking entry | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_onboarding_api_key_deferral_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_onboarding_api_key_deferral_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend onboarding API-key deferral | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_main_page_api_key_config_entry_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_main_page_api_key_config_entry_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend main-page API-key config entry | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_public_asset_path_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_public_asset_path_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend public asset path guard | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_bot_tool_config_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_bot_tool_config_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend bot/tool config error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_market_universe_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_market_universe_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend market-universe error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_frontend_market_symbol_sanitizer_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_frontend_market_symbol_sanitizer_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading frontend market symbol sanitizer | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_private_factor_result_schema_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_private_factor_per_user_result_schema_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading private factor per-user result schema | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_agent_session_id_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_agent_session_id_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading agent-session id safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_agent_session_id_validation_error_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_agent_session_id_validation_error_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading agent-session id validation error safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_agent_session_name_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_agent_session_name_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading agent-session name safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_strategy_spec_name_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_strategy_spec_name_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading strategy-spec name safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_handoff_error_message_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_handoff_error_message_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading handoff error-message safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_handoff_confirmation_source_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_handoff_confirmation_source_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading handoff confirmation-source safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_signal_rejection_reason_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_signal_rejection_reason_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading signal rejection reason safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_backtest_evidence_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_backtest_evidence_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading backtest evidence safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_market_context_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_market_context_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading market context safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_strategy_text_source_safety_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_strategy_text_source_safety_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading strategy text source safety | Done |"
        in status_evidence["missing_phrases"]
    )


def test_completion_audit_blocks_local_acceptance_when_gateway_mode_guard_marker_is_missing(tmp_path):
    _write_minimal_acceptance_repo(
        tmp_path,
        include_gateway_mode_guard_marker=False,
    )

    report = completion_audit.build_completion_report(tmp_path)

    assert report["local_v1_accepted"] is False
    assert "status_progress_marker" in report["summary"]["local_blockers"]
    status_evidence = next(item for item in report["local_evidence"] if item["id"] == "status_progress_marker")
    assert status_evidence["status"] == "incomplete_evidence"
    assert (
        "| AI Trading gateway mode guard | Done |"
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


def test_completion_audit_rejects_generic_accepted_production_evidence_summary(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    evidence_path = _outside_repo_evidence_path(tmp_path, "generic-summary-production-evidence.json")
    _write_production_evidence(evidence_path)
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    payload["items"]["real_order_backend_handoff"]["evidence_summary"] = (
        "Real order backend handoff accepted with sanitized operational evidence."
    )
    _write(evidence_path, json.dumps(payload, indent=2, sort_keys=True))

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=evidence_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    assert "external_evidence_item_blocked:real_order_backend_handoff" in report["production_evidence"]["blockers"]
    item = next(
        item
        for item in report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert item["missing_summary_terms"] == [
        "HTTPS",
        "mode=http / gateway mode=http / gateway_mode=http",
        "token-present / token present / token_present",
        "production_handoff_approved=true / production approval / approved production handoff",
    ]
    assert "external_evidence_summary_missing_required_term:https" in item["blockers"]
    assert "external_evidence_summary_missing_required_term:mode_http" in item["blockers"]
    assert "external_evidence_summary_missing_required_term:token_present" in item["blockers"]
    assert "external_evidence_summary_missing_required_term:production_handoff_approved_true" in item["blockers"]


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
    future_generated_path = tmp_path / "future-generated-at-evidence.json"
    future_validated_path = tmp_path / "future-validated-at-evidence.json"
    stale_validated_path = tmp_path / "stale-validated-at-evidence.json"
    _write_production_evidence(missing_generated_path, generated_at=None)
    _write_production_evidence(invalid_validated_path, validated_at="2026/06/10 12:00 UTC")
    _write_production_evidence(timezone_missing_path, generated_at="2026-06-10T12:05:00")
    _write_production_evidence(
        generated_before_validated_path,
        generated_at=_utc_iso(timedelta(minutes=-10)),
        validated_at=_utc_iso(timedelta(minutes=-5)),
    )
    _write_production_evidence(
        future_generated_path,
        generated_at=_utc_iso(timedelta(minutes=30)),
        expires_at=_utc_iso(timedelta(days=1)),
    )
    _write_production_evidence(
        future_validated_path,
        generated_at=_utc_iso(timedelta(minutes=-1)),
        validated_at=_utc_iso(timedelta(minutes=30)),
    )
    _write_production_evidence(
        stale_validated_path,
        generated_at=_utc_iso(timedelta(minutes=-1)),
        validated_at=_utc_iso(timedelta(days=-8)),
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
    future_generated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=future_generated_path,
        allow_live_ready_from_evidence=True,
    )
    future_validated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=future_validated_path,
        allow_live_ready_from_evidence=True,
    )
    stale_validated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=stale_validated_path,
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
    assert future_generated_report["ready_for_live_orders"] is False
    assert "external_evidence_generated_at_in_future" in future_generated_report["production_evidence"]["blockers"]
    assert future_validated_report["ready_for_live_orders"] is False
    future_validated_item = next(
        item
        for item in future_validated_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_at_in_future" in future_validated_item["blockers"]
    assert stale_validated_report["ready_for_live_orders"] is False
    stale_validated_item = next(
        item
        for item in stale_validated_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_validated_at_too_old" in stale_validated_item["blockers"]


def test_completion_audit_rejects_missing_or_expired_production_evidence_expiry(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    missing_expiry_path = tmp_path / "missing-expiry-evidence.json"
    invalid_expiry_path = tmp_path / "invalid-expiry-evidence.json"
    expired_path = tmp_path / "expired-evidence.json"
    expiry_before_generated_path = tmp_path / "expiry-before-generated-evidence.json"
    expiry_too_far_path = tmp_path / "expiry-too-far-evidence.json"
    _write_production_evidence(missing_expiry_path, expires_at=None)
    _write_production_evidence(invalid_expiry_path, expires_at="2099-06-10T12:05:00")
    _write_production_evidence(expired_path, expires_at="2000-01-01T00:00:00Z")
    _write_production_evidence(
        expiry_before_generated_path,
        generated_at=_utc_iso(timedelta(minutes=-5)),
        expires_at=_utc_iso(timedelta(minutes=-10)),
    )
    _write_production_evidence(
        expiry_too_far_path,
        generated_at=_utc_iso(timedelta(minutes=-5)),
        expires_at=_utc_iso(timedelta(days=8)),
    )

    missing_expiry_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=missing_expiry_path,
        allow_live_ready_from_evidence=True,
    )
    invalid_expiry_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=invalid_expiry_path,
        allow_live_ready_from_evidence=True,
    )
    expired_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=expired_path,
        allow_live_ready_from_evidence=True,
    )
    expiry_before_generated_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=expiry_before_generated_path,
        allow_live_ready_from_evidence=True,
    )
    expiry_too_far_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=expiry_too_far_path,
        allow_live_ready_from_evidence=True,
    )

    assert missing_expiry_report["ready_for_live_orders"] is False
    assert "external_evidence_expires_at_missing" in missing_expiry_report["production_evidence"]["blockers"]
    assert invalid_expiry_report["ready_for_live_orders"] is False
    assert "external_evidence_expires_at_timezone_missing" in invalid_expiry_report["production_evidence"]["blockers"]
    assert expired_report["ready_for_live_orders"] is False
    assert "external_evidence_expired" in expired_report["production_evidence"]["blockers"]
    assert expiry_before_generated_report["ready_for_live_orders"] is False
    assert (
        "external_evidence_expires_at_not_after_generated_at"
        in expiry_before_generated_report["production_evidence"]["blockers"]
    )
    assert expiry_too_far_report["ready_for_live_orders"] is False
    assert "external_evidence_expires_at_too_far" in expiry_too_far_report["production_evidence"]["blockers"]


def test_completion_audit_rejects_missing_or_invalid_cutover_window(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    missing_window_path = tmp_path / "missing-cutover-window-evidence.json"
    unexpected_field_path = tmp_path / "unexpected-cutover-window-field-evidence.json"
    future_window_path = tmp_path / "future-cutover-window-evidence.json"
    ended_window_path = tmp_path / "ended-cutover-window-evidence.json"
    too_long_window_path = tmp_path / "too-long-cutover-window-evidence.json"
    generated_before_window_path = tmp_path / "generated-before-cutover-window-evidence.json"
    _write_production_evidence(missing_window_path, cutover_window=None)
    _write_production_evidence(
        unexpected_field_path,
        cutover_window={
            "start_at": _utc_iso(timedelta(minutes=-10)),
            "end_at": _utc_iso(timedelta(hours=2)),
            "raw_window_note": "not allowed",
        },
    )
    _write_production_evidence(
        future_window_path,
        cutover_window={
            "start_at": _utc_iso(timedelta(hours=1)),
            "end_at": _utc_iso(timedelta(hours=2)),
        },
    )
    _write_production_evidence(
        ended_window_path,
        generated_at=_utc_iso(timedelta(hours=-2)),
        validated_at=_utc_iso(timedelta(hours=-2, minutes=-5)),
        expires_at=_utc_iso(timedelta(days=1)),
        cutover_window={
            "start_at": _utc_iso(timedelta(hours=-3)),
            "end_at": _utc_iso(timedelta(hours=-1)),
        },
    )
    _write_production_evidence(
        too_long_window_path,
        cutover_window={
            "start_at": _utc_iso(timedelta(minutes=-10)),
            "end_at": _utc_iso(timedelta(hours=9)),
        },
    )
    _write_production_evidence(
        generated_before_window_path,
        generated_at=_utc_iso(timedelta(minutes=-20)),
        validated_at=_utc_iso(timedelta(minutes=-25)),
        expires_at=_utc_iso(timedelta(days=1)),
        cutover_window={
            "start_at": _utc_iso(timedelta(minutes=-5)),
            "end_at": _utc_iso(timedelta(hours=2)),
        },
    )

    missing_window_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=missing_window_path,
        allow_live_ready_from_evidence=True,
    )
    unexpected_field_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=unexpected_field_path,
        allow_live_ready_from_evidence=True,
    )
    future_window_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=future_window_path,
        allow_live_ready_from_evidence=True,
    )
    ended_window_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=ended_window_path,
        allow_live_ready_from_evidence=True,
    )
    too_long_window_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=too_long_window_path,
        allow_live_ready_from_evidence=True,
    )
    generated_before_window_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=generated_before_window_path,
        allow_live_ready_from_evidence=True,
    )

    assert missing_window_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_window_missing" in missing_window_report["production_evidence"]["blockers"]
    assert missing_window_report["production_evidence"]["cutover_window_present"] is False
    assert unexpected_field_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_window_unexpected_fields" in unexpected_field_report["production_evidence"]["blockers"]
    assert unexpected_field_report["production_evidence"]["cutover_window_unexpected_fields"] == ["raw_window_note"]
    assert future_window_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_window_not_started" in future_window_report["production_evidence"]["blockers"]
    assert ended_window_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_window_ended" in ended_window_report["production_evidence"]["blockers"]
    assert too_long_window_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_window_too_long" in too_long_window_report["production_evidence"]["blockers"]
    assert generated_before_window_report["ready_for_live_orders"] is False
    assert (
        "external_evidence_generated_at_before_cutover_window"
        in generated_before_window_report["production_evidence"]["blockers"]
    )


def test_completion_audit_rejects_missing_or_invalid_evidence_run_id(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    missing_run_id_path = tmp_path / "missing-run-id-evidence.json"
    short_run_id_path = tmp_path / "short-run-id-evidence.json"
    long_run_id_path = tmp_path / "long-run-id-evidence.json"
    placeholder_run_id_path = tmp_path / "placeholder-run-id-evidence.json"
    invalid_chars_run_id_path = tmp_path / "invalid-chars-run-id-evidence.json"
    _write_production_evidence(missing_run_id_path, evidence_run_id=None)
    _write_production_evidence(short_run_id_path, evidence_run_id="run-1")
    _write_production_evidence(long_run_id_path, evidence_run_id="ops-" + "x" * 81)
    _write_production_evidence(placeholder_run_id_path, evidence_run_id="placeholder")
    _write_production_evidence(
        invalid_chars_run_id_path,
        evidence_run_id="https://ops.hyperalpha.org/cutover/run/001",
    )

    missing_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=missing_run_id_path,
        allow_live_ready_from_evidence=True,
    )
    short_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=short_run_id_path,
        allow_live_ready_from_evidence=True,
    )
    long_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=long_run_id_path,
        allow_live_ready_from_evidence=True,
    )
    placeholder_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=placeholder_run_id_path,
        allow_live_ready_from_evidence=True,
    )
    invalid_chars_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=invalid_chars_run_id_path,
        allow_live_ready_from_evidence=True,
    )

    assert missing_run_id_report["ready_for_live_orders"] is False
    assert "external_evidence_run_id_missing" in missing_run_id_report["production_evidence"]["blockers"]
    assert missing_run_id_report["production_evidence"]["evidence_run_id_present"] is False
    assert short_run_id_report["ready_for_live_orders"] is False
    assert "external_evidence_run_id_too_short" in short_run_id_report["production_evidence"]["blockers"]
    assert long_run_id_report["ready_for_live_orders"] is False
    assert "external_evidence_run_id_too_long" in long_run_id_report["production_evidence"]["blockers"]
    assert placeholder_run_id_report["ready_for_live_orders"] is False
    assert "external_evidence_run_id_placeholder" in placeholder_run_id_report["production_evidence"]["blockers"]
    assert invalid_chars_run_id_report["ready_for_live_orders"] is False
    assert "external_evidence_run_id_invalid_chars" in invalid_chars_run_id_report["production_evidence"]["blockers"]


def test_completion_audit_rejects_refs_that_do_not_contain_evidence_run_id(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    approval_missing_run_id_path = tmp_path / "approval-ref-missing-run-id-evidence.json"
    artifact_missing_run_id_path = tmp_path / "artifact-ref-missing-run-id-evidence.json"
    _write_production_evidence(
        approval_missing_run_id_path,
        cutover_approval_ref="ops://ai-trading/other-run/production-cutover/approval",
    )
    _write_production_evidence(
        artifact_missing_run_id_path,
        artifact_ref_override="ops://ai-trading/other-run/real-order-backend-handoff/acceptance",
    )

    approval_missing_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=approval_missing_run_id_path,
        allow_live_ready_from_evidence=True,
    )
    artifact_missing_run_id_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=artifact_missing_run_id_path,
        allow_live_ready_from_evidence=True,
    )

    assert approval_missing_run_id_report["ready_for_live_orders"] is False
    assert (
        "external_evidence_cutover_approval_ref_missing_run_id"
        in approval_missing_run_id_report["production_evidence"]["blockers"]
    )
    assert artifact_missing_run_id_report["ready_for_live_orders"] is False
    order_backend_item = next(
        item
        for item in artifact_missing_run_id_report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_ref_missing_run_id" in order_backend_item["blockers"]


def test_completion_audit_rejects_refs_that_do_not_contain_item_id(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    artifact_missing_item_id_path = tmp_path / "artifact-ref-missing-item-id-evidence.json"
    _write_production_evidence(
        artifact_missing_item_id_path,
        artifact_ref_override="ops://ai-trading/ops-20260610-cutover-001/generic-acceptance",
    )

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=artifact_missing_item_id_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    order_backend_item = next(
        item
        for item in report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_ref_missing_item_id" in order_backend_item["blockers"]
    assert "external_evidence_artifact_ref_missing_run_id" not in order_backend_item["blockers"]


def test_completion_audit_rejects_artifact_refs_reused_across_items(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    duplicate_ref_path = tmp_path / "duplicate-artifact-ref-evidence.json"
    _write_production_evidence(duplicate_ref_path)
    payload = json.loads(duplicate_ref_path.read_text(encoding="utf-8"))
    duplicate_ref = (
        "ops://ai-trading/ops-20260610-cutover-001/"
        "real_order_backend_handoff/production_auth_hard_risk_readiness/shared-acceptance"
    )
    payload["items"]["real_order_backend_handoff"]["artifact_refs"] = [duplicate_ref]
    payload["items"]["production_auth_hard_risk_readiness"]["artifact_refs"] = [duplicate_ref]
    duplicate_ref_path.write_text(json.dumps(payload), encoding="utf-8")

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=duplicate_ref_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    items_by_id = {item["id"]: item for item in report["production_evidence"]["items"]}
    assert (
        "external_evidence_artifact_ref_reused_across_items"
        in items_by_id["real_order_backend_handoff"]["blockers"]
    )
    assert (
        "external_evidence_artifact_ref_reused_across_items"
        in items_by_id["production_auth_hard_risk_readiness"]["blockers"]
    )
    assert "external_evidence_artifact_ref_missing_item_id" not in items_by_id["real_order_backend_handoff"]["blockers"]
    assert (
        "external_evidence_artifact_ref_missing_item_id"
        not in items_by_id["production_auth_hard_risk_readiness"]["blockers"]
    )


def test_completion_audit_rejects_duplicate_artifact_refs_inside_item(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    duplicate_ref_path = tmp_path / "duplicate-artifact-ref-in-item-evidence.json"
    _write_production_evidence(duplicate_ref_path)
    payload = json.loads(duplicate_ref_path.read_text(encoding="utf-8"))
    duplicate_ref = "ops://ai-trading/ops-20260610-cutover-001/real_order_backend_handoff/acceptance"
    payload["items"]["real_order_backend_handoff"]["artifact_refs"] = [
        duplicate_ref,
        duplicate_ref + " ",
    ]
    duplicate_ref_path.write_text(json.dumps(payload), encoding="utf-8")

    report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=duplicate_ref_path,
        allow_live_ready_from_evidence=True,
    )

    assert report["ready_for_live_orders"] is False
    order_backend_item = next(
        item
        for item in report["production_evidence"]["items"]
        if item["id"] == "real_order_backend_handoff"
    )
    assert "external_evidence_artifact_ref_duplicate_in_item" in order_backend_item["blockers"]
    assert "external_evidence_artifact_ref_reused_across_items" not in order_backend_item["blockers"]
    assert "external_evidence_artifact_ref_missing_item_id" not in order_backend_item["blockers"]


def test_completion_audit_rejects_missing_or_unsafe_cutover_approval_ref(tmp_path):
    _write_minimal_acceptance_repo(tmp_path)
    missing_ref_path = tmp_path / "missing-cutover-approval-ref-evidence.json"
    local_ref_path = tmp_path / "local-cutover-approval-ref-evidence.json"
    secret_ref_path = tmp_path / "secret-cutover-approval-ref-evidence.json"
    _write_production_evidence(missing_ref_path, cutover_approval_ref=None)
    _write_production_evidence(local_ref_path, cutover_approval_ref="http://127.0.0.1:8802/approval")
    _write_production_evidence(
        secret_ref_path,
        cutover_approval_ref="ops://ai-trading/cutover?access_token=secret-production-token-123456",
    )

    missing_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=missing_ref_path,
        allow_live_ready_from_evidence=True,
    )
    local_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=local_ref_path,
        allow_live_ready_from_evidence=True,
    )
    secret_ref_report = completion_audit.build_completion_report(
        tmp_path,
        production_evidence_file=secret_ref_path,
        allow_live_ready_from_evidence=True,
    )

    assert missing_ref_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_approval_ref_missing" in missing_ref_report["production_evidence"]["blockers"]
    assert missing_ref_report["production_evidence"]["cutover_approval_ref_present"] is False
    assert local_ref_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_approval_ref_scheme_not_allowed" in local_ref_report["production_evidence"]["blockers"]
    assert "external_evidence_cutover_approval_ref_local_host" in local_ref_report["production_evidence"]["blockers"]
    assert secret_ref_report["ready_for_live_orders"] is False
    assert "external_evidence_cutover_approval_ref_secret_pattern_detected" in secret_ref_report["production_evidence"]["blockers"]
    assert "external_evidence_secret_pattern_detected" in secret_ref_report["production_evidence"]["blockers"]


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
        "validated_at": _utc_iso(timedelta(minutes=-5)),
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
