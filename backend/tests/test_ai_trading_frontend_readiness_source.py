from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PAGE = REPO_ROOT / "frontend" / "app" / "components" / "settings" / "SettingsPage.tsx"
FRONTEND_MAIN = REPO_ROOT / "frontend" / "app" / "main.tsx"
APP_ERROR_BOUNDARY = REPO_ROOT / "frontend" / "app" / "components" / "layout" / "AppErrorBoundary.tsx"
CONTACT_DIALOG = REPO_ROOT / "frontend" / "app" / "components" / "contact" / "ContactDialog.tsx"
HYPER_AI_PAGE = REPO_ROOT / "frontend" / "app" / "components" / "hyper-ai" / "HyperAiPage.tsx"
HYPER_AI_ONBOARDING = REPO_ROOT / "frontend" / "app" / "components" / "hyper-ai" / "HyperAiOnboarding.tsx"
BOT_INTEGRATION_MODAL = REPO_ROOT / "frontend" / "app" / "components" / "hyper-ai" / "BotIntegrationModal.tsx"
TOOL_CONFIG_MODAL = REPO_ROOT / "frontend" / "app" / "components" / "hyper-ai" / "ToolConfigModal.tsx"
HYPERLIQUID_WALLET_SECTION = REPO_ROOT / "frontend" / "app" / "components" / "trader" / "HyperliquidWalletSection.tsx"
WALLET_CONFIG_PANEL = REPO_ROOT / "frontend" / "app" / "components" / "trader" / "WalletConfigPanel.tsx"
BINANCE_WALLET_SECTION = REPO_ROOT / "frontend" / "app" / "components" / "trader" / "BinanceWalletSection.tsx"
READINESS_HELPER = REPO_ROOT / "frontend" / "app" / "lib" / "aiTradingReadiness.ts"
POLL_AI_STREAM_HELPER = REPO_ROOT / "frontend" / "app" / "lib" / "pollAiStream.ts"


def test_admin_readiness_context_locator_ui_uses_secret_safe_projection() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")

    assert "extractAiTradingAgentContextLocators" in settings_source
    assert "latest_over_budget" in settings_source
    assert "latest_redacted_context" in settings_source
    assert "latest_sensitive_context" in settings_source
    assert "agentSessionId" in settings_source
    assert "contextSummaryChars" in settings_source
    assert "context_summary" not in settings_source

    assert "agent_session_id" in helper_source
    assert "context_summary_chars" in helper_source
    helper_without_allowed_locator_fields = (
        helper_source
        .replace("agent_session_id", "")
        .replace("context_summary_chars", "")
    )
    assert "context_summary" not in helper_without_allowed_locator_fields


def test_admin_production_evidence_explain_ui_uses_safe_projection() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    helper_projection_source = (
        helper_source.split("const PRODUCTION_EVIDENCE_BLOCKER_LABELS", 1)[0]
        + helper_source.split("export const extractAiTradingAgentContextLocators", 1)[1]
    )

    assert "/api/ai-trading/admin/production-evidence-explain" in settings_source
    assert "extractAiTradingProductionEvidenceExplain" in settings_source
    assert "AiTradingProductionEvidenceExplainView" in settings_source
    assert "productionEvidence.acceptedCount" in settings_source
    assert "productionEvidence.evidenceRunIdPresent" in settings_source
    assert "productionEvidence.expiresAt" in settings_source
    assert "productionEvidence.cutoverWindowPresent" in settings_source
    assert "productionEvidence.cutoverWindowStartAt" in settings_source
    assert "productionEvidence.cutoverWindowEndAt" in settings_source
    assert "productionEvidence.cutoverApprovalRefPresent" in settings_source
    assert "maxEvidenceValidityDays" in settings_source
    assert "maxClockSkewSeconds" in settings_source
    assert "maxItemValidationAgeDays" in settings_source
    assert "maxCutoverWindowHours" in settings_source
    assert "minEvidenceRunIdChars" in settings_source
    assert "maxEvidenceRunIdChars" in settings_source
    assert "readyForLiveOrders" in settings_source
    assert "progress.acceptedCount" in settings_source
    assert "progress.pendingCount" in settings_source
    assert "progress.blockedCount" in settings_source
    assert "progress.requiredCount" in settings_source
    assert "progress.liveOrderGateBlockers" in settings_source
    assert "progress.nextRequiredItemIds" in settings_source
    assert "progress.nextRequiredActions" in settings_source
    assert "progress.rootNextRequiredActions" in settings_source
    assert "artifactRefCount" in settings_source
    assert "requiredSummaryTerms" in settings_source
    assert "missingSummaryTerms" in settings_source
    assert "operatorGuidance" in settings_source
    assert "evidence_summary" not in settings_source
    assert "production_evidence_file" not in settings_source
    assert "AI_TRADING_SIGNAL_GATEWAY_TOKEN" not in settings_source
    assert "DEEPSEEK_API_KEY" not in settings_source
    assert "QWEN_API_KEY" not in settings_source
    assert "DASHSCOPE_API_KEY" not in settings_source

    assert "production_evidence" in helper_source
    assert "progress" in helper_source
    assert "ready_for_live_orders" in helper_source
    assert "evidence_run_id_present" in helper_source
    assert "expires_at" in helper_source
    assert "cutover_window_present" in helper_source
    assert "cutover_window_start_at" in helper_source
    assert "cutover_window_end_at" in helper_source
    assert "cutover_approval_ref_present" in helper_source
    assert "max_evidence_validity_days" in helper_source
    assert "max_clock_skew_seconds" in helper_source
    assert "max_item_validation_age_days" in helper_source
    assert "max_cutover_window_hours" in helper_source
    assert "min_evidence_run_id_chars" in helper_source
    assert "max_evidence_run_id_chars" in helper_source
    assert "artifact_ref_count" in helper_source
    assert "accepted_item_ids" in helper_source
    assert "pending_item_ids" in helper_source
    assert "blocked_item_ids" in helper_source
    assert "next_required_item_ids" in helper_source
    assert "next_required_actions" in helper_source
    assert "root_next_required_actions" in helper_source
    assert "live_order_gate_blockers" in helper_source
    assert "required_summary_terms" in helper_source
    assert "missing_summary_terms" in helper_source
    assert "operator_guidance" in helper_source
    assert "evidence_summary" not in helper_projection_source
    helper_without_safe_cutover_fields = (
        helper_projection_source
        .replace("cutover_window_present", "")
        .replace("cutover_window_start_at", "")
        .replace("cutover_window_end_at", "")
        .replace("max_cutover_window_hours", "")
    )
    assert "cutover_window" not in helper_without_safe_cutover_fields
    helper_without_safe_run_id_fields = (
        helper_projection_source
        .replace("evidence_run_id_present", "")
        .replace("min_evidence_run_id_chars", "")
        .replace("max_evidence_run_id_chars", "")
    )
    assert "evidence_run_id" not in helper_without_safe_run_id_fields
    assert "cutover_approval_ref\"" not in helper_projection_source
    assert "secret_values_returned" not in helper_projection_source
    assert "production_evidence_file" not in helper_source


def test_admin_production_readiness_ui_uses_safe_api_error_formatter() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    readiness_loader_block = settings_source.split(
        "const fetchAiTradingReadiness",
        1,
    )[1].split("const fetchAiTradingEvidenceExplain", 1)[0]

    assert "formatAiTradingProductionReadinessApiError" in settings_source
    assert "formatAiTradingProductionReadinessApiError" in helper_source
    assert "PRODUCTION_READINESS_API_DETAIL_LABELS" in helper_source
    assert "PRODUCTION_READINESS_API_STATUS_LABELS" in helper_source
    assert "Admin authentication required" in helper_source
    assert "AI Trading production readiness service failed" in helper_source

    assert "formatAiTradingProductionReadinessApiError(res.status, data.detail, fallback)" in readiness_loader_block
    assert "formatAiTradingProductionReadinessApiError(0, null, fallback)" in readiness_loader_block
    assert "throw new Error(data.detail" not in readiness_loader_block
    assert "data.detail ||" not in readiness_loader_block
    assert "err instanceof Error ? err.message" not in readiness_loader_block
    assert "setAiTradingReadinessError(err" not in readiness_loader_block


def test_admin_ai_runtime_ui_uses_safe_api_error_formatter() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    runtime_loader_block = settings_source.split(
        "const fetchAiRuntimeStats",
        1,
    )[1].split("const fetchAiTradingReadiness", 1)[0]

    assert "/api/ai-stream/admin/runtime" in runtime_loader_block
    assert "formatAiTradingAiRuntimeApiError" in settings_source
    assert "formatAiTradingAiRuntimeApiError" in helper_source
    assert "AI_RUNTIME_API_DETAIL_LABELS" in helper_source
    assert "AI_RUNTIME_API_STATUS_LABELS" in helper_source
    assert "Admin authentication required" in helper_source
    assert "AI runtime service failed" in helper_source

    assert "formatAiTradingAiRuntimeApiError(res.status, data.detail, fallback)" in runtime_loader_block
    assert "formatAiTradingAiRuntimeApiError(0, null, fallback)" in runtime_loader_block
    assert "throw new Error(data.detail" not in runtime_loader_block
    assert "data.detail ||" not in runtime_loader_block
    assert "err instanceof Error ? err.message" not in runtime_loader_block
    assert "setAiRuntimeError(err" not in runtime_loader_block


def test_admin_ai_runtime_ui_redacts_component_last_errors() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    runtime_display_block = settings_source.split(
        "settings.distributedAdmission",
        1,
    )[1].split("{aiRuntimeStats.users.length", 1)[0]

    assert "formatAiTradingAiRuntimeLastError" in settings_source
    assert "formatAiTradingAiRuntimeLastError" in helper_source
    assert "AI_RUNTIME_LAST_ERROR_LABELS" in helper_source
    assert "distributed_admission_unavailable" in helper_source
    assert "dispatch_queue_stats_unavailable" in helper_source
    assert "last_error_present" in runtime_display_block
    assert "last_error_code" in runtime_display_block
    assert "{aiRuntimeStats.distributed_admission.last_error}" not in runtime_display_block
    assert "{aiRuntimeStats.dispatch_queue.last_error}" not in runtime_display_block


def test_poll_ai_stream_uses_safe_error_formatters() -> None:
    poll_source = POLL_AI_STREAM_HELPER.read_text(encoding="utf-8")

    assert "POLL_AI_STREAM_PUBLIC_ERROR_MESSAGE" in poll_source
    assert "POLL_AI_STREAM_TIMEOUT_ERROR_MESSAGE" in poll_source
    assert "POLL_AI_STREAM_TASK_ERROR_MESSAGE" in poll_source
    assert "POLL_AI_STREAM_STATUS_ERROR_LABELS" in poll_source
    assert "POLL_AI_STREAM_SAFE_TASK_ERROR_VALUES" in poll_source
    assert "POLL_AI_STREAM_SAFE_NETWORK_ERROR_VALUES" in poll_source
    assert "function formatPollAiStreamTaskError" in poll_source
    assert "function formatPollAiStreamHttpError" in poll_source
    assert "function formatPollAiStreamNetworkError" in poll_source

    assert "return { status: 'timeout', error: POLL_AI_STREAM_TIMEOUT_ERROR_MESSAGE }" in poll_source
    assert "throw new Error(formatPollAiStreamHttpError(res.status))" in poll_source
    assert "return { status: 'error', error: formatPollAiStreamTaskError(error) }" in poll_source
    assert "const safeMessage = formatPollAiStreamNetworkError(e)" in poll_source
    assert "options.onError?.(new Error(safeMessage))" in poll_source
    assert "return { status: 'network_error', error: safeMessage }" in poll_source

    assert "Polling exceeded max duration" not in poll_source
    assert "throw new Error(`Poll returned ${res.status}`)" not in poll_source
    assert "error || 'Task failed'" not in poll_source
    assert "String(e)" not in poll_source
    assert "error: err.message" not in poll_source
    assert "options.onError?.(err)" not in poll_source


def test_admin_production_evidence_validate_ui_uses_safe_projection() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    explain_block = settings_source.split("const fetchAiTradingEvidenceExplain", 1)[1].split(
        "const validateAiTradingEvidence",
        1,
    )[0]
    validate_block = settings_source.split("const validateAiTradingEvidence", 1)[1].split(
        "const loadAiTradingEvidenceTemplate",
        1,
    )[0]
    template_block = settings_source.split("const loadAiTradingEvidenceTemplate", 1)[1].split(
        "const fetchAdminData",
        1,
    )[0]

    assert "/api/ai-trading/admin/production-evidence-template" in settings_source
    assert "/api/ai-trading/admin/production-evidence-validate" in settings_source
    assert "loadAiTradingEvidenceTemplate" in settings_source
    assert "extractAiTradingProductionEvidenceTemplateGuidance(data.guidance)" in settings_source
    assert "extractAiTradingProductionEvidenceDryRun(data.dry_run)" in settings_source
    assert "formatAiTradingProductionEvidenceApiError" in settings_source
    assert "formatAiTradingProductionEvidenceApiError" in helper_source
    assert "PRODUCTION_EVIDENCE_API_ERROR_LABELS" in helper_source
    assert "PRODUCTION_EVIDENCE_API_STATUS_LABELS" in helper_source
    assert "safeProductionEvidenceApiDetailCode" in helper_source
    assert "production_evidence_payload_too_large" in helper_source
    assert "production_evidence_items_too_many" in helper_source
    assert "Admin authentication required" in helper_source
    assert "Admin role required" in helper_source
    for safe_error_block in (explain_block, validate_block, template_block):
        assert "formatAiTradingProductionEvidenceApiError(res.status, data.detail" in safe_error_block
        assert "formatAiTradingProductionEvidenceApiError(0, null" in safe_error_block
        assert "throw new Error(data.detail" not in safe_error_block
        assert "data.detail ||" not in safe_error_block
        assert "err instanceof Error ? err.message" not in safe_error_block
    assert "aiTradingEvidenceDryRun.payloadBytes" in settings_source
    assert "aiTradingEvidenceDryRun.maxPayloadBytes" in settings_source
    assert "aiTradingEvidenceDryRun.itemKeyCount" in settings_source
    assert "aiTradingEvidenceDryRun.maxItemKeys" in settings_source
    assert "aiTradingEvidenceDryRun.rootIsObject" in settings_source
    assert "aiTradingEvidenceDryRun.expectedInput" in settings_source
    assert "aiTradingEvidenceDryRun.liveOrdersUnlocked" in settings_source
    assert "formatAiTradingEvidenceDryRunCalls(aiTradingEvidenceDryRun)" in settings_source
    assert "aiTradingEvidenceTemplateGuidance.nextRequiredActions" in settings_source
    assert "aiTradingEvidenceTemplateGuidance.rootNextRequiredActions" in settings_source
    assert "aiTradingEvidenceTemplateGuidance.rootFields.length" in settings_source
    assert "aiTradingEvidenceTemplateGuidance.rootFields.map" in settings_source
    assert "field.requiredValue" in settings_source
    assert "field.operatorGuidance[0]" in settings_source
    assert "field.relatedBlockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker)" in settings_source
    assert "aiTradingEvidenceTemplateGuidance.items.slice(0, 4).map" in settings_source
    assert "item.requiredSummaryTerms.slice(0, 2).join(', ')" in settings_source
    assert "item.operatorGuidance[0] || item.description" in settings_source
    assert "setAiTradingEvidenceTemplateGuidance(" in settings_source
    assert "extractAiTradingProductionEvidenceTemplateGuidance(data.guidance)" in settings_source
    assert "item.missingSummaryTerms.slice(0, 2).join(', ')" in settings_source
    assert "item.operatorGuidance[0]" in settings_source
    assert "settings.aiTradingEvidenceFixHint" in settings_source
    assert "extractAiTradingProductionEvidenceTemplateGuidance" in helper_source
    assert "extractAiTradingProductionEvidenceDryRun" in helper_source
    assert "secret_policy" in helper_source
    assert "payload_bytes" in helper_source
    assert "max_payload_bytes" in helper_source
    assert "item_key_count" in helper_source
    assert "max_item_keys" in helper_source
    assert "root_is_object" in helper_source
    assert "expected_input" in helper_source
    assert "live_orders_unlocked" in helper_source
    assert "network_calls" in helper_source
    assert "order_backend_calls" in helper_source
    assert "root_fields" in helper_source
    assert "root_next_required_actions" in helper_source
    assert "related_blockers" in helper_source
    assert "next_required_actions" in helper_source
    assert "safe_artifact_ref_schemes" in helper_source
    assert "AI_TRADING_EVIDENCE_MAX_JSON_CHARS" in settings_source
    assert "aiTradingEvidenceValidationTooLarge" in settings_source
    assert "maxLength={AI_TRADING_EVIDENCE_MAX_JSON_CHARS}" in settings_source
    assert "aiTradingEvidenceValidationJson" in settings_source
    assert "aiTradingEvidenceValidation.productionEvidence.acceptedCount" in settings_source
    assert "aiTradingEvidenceValidation.productionEvidence.evidenceRunIdPresent" in settings_source
    assert "aiTradingEvidenceValidation.productionEvidence.expiresAt" in settings_source
    assert "aiTradingEvidenceValidation.productionEvidence.cutoverWindowPresent" in settings_source
    assert "aiTradingEvidenceValidation.maxClockSkewSeconds" in settings_source
    assert "aiTradingEvidenceValidation.maxItemValidationAgeDays" in settings_source
    assert "aiTradingEvidenceValidation.maxCutoverWindowHours" in settings_source
    assert "aiTradingEvidenceValidation.minEvidenceRunIdChars" in settings_source
    assert "aiTradingEvidenceValidation.maxEvidenceRunIdChars" in settings_source
    assert "aiTradingEvidenceValidation.readyForLiveOrders" in settings_source
    assert "aiTradingEvidenceValidation.progress.pendingCount" in settings_source
    assert "aiTradingEvidenceValidation.progress.liveOrderGateBlockers" in settings_source
    assert "aiTradingEvidenceValidation.progress.nextRequiredItemIds" in settings_source
    assert "aiTradingEvidenceValidation.progress.rootNextRequiredActions" in settings_source
    assert "extractAiTradingProductionEvidenceExplain(data.validation)" in settings_source
    assert "JSON.stringify(data.template || {}, null, 2)" in settings_source
    assert "production_evidence_file" not in settings_source
    assert "AI_TRADING_SIGNAL_GATEWAY_TOKEN" not in settings_source
    assert "DEEPSEEK_API_KEY" not in settings_source
    assert "QWEN_API_KEY" not in settings_source
    assert "DASHSCOPE_API_KEY" not in settings_source


def test_admin_production_evidence_blockers_use_readable_labels() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")

    assert "formatAiTradingProductionEvidenceBlocker" in settings_source
    assert "formatAiTradingProductionEvidenceBlocker" in helper_source
    assert "external_evidence_artifact_ref_duplicate_in_item" in helper_source
    assert "Duplicate artifact ref in item" in helper_source
    assert "external_evidence_artifact_ref_reused_across_items" in helper_source
    assert "Artifact ref reused across items" in helper_source
    assert "external_evidence_cutover_window_start_at_missing" in helper_source
    assert "Cutover window start time missing" in helper_source
    assert "external_evidence_cutover_window_end_at_missing" in helper_source
    assert "Cutover window end time missing" in helper_source
    assert "external_evidence_summary_missing" in helper_source
    assert "Evidence summary missing" in helper_source
    assert "external_evidence_validated_by_missing" in helper_source
    assert "Validator name missing" in helper_source
    assert "production_evidence_not_ready" in helper_source
    assert "Production evidence is not ready" in helper_source
    assert "explicit_live_ready_confirmation_required" in helper_source
    assert "Explicit live-order confirmation required" in helper_source
    assert "external_evidence_item_blocked:" in helper_source
    assert "external_evidence_summary_missing_required_term:" in helper_source

    explain_root_block = settings_source.split(
        "aiTradingEvidenceExplain.productionEvidence.blockers.length > 0",
        1,
    )[1].split("aiTradingEvidenceExplain.items.map((item) => (", 1)[0]
    explain_block = settings_source.split(
        "aiTradingEvidenceExplain.items.map((item) => (",
        1,
    )[1].split("aiTradingEvidenceExplain.nextActions.length", 1)[0]
    validation_block = settings_source.split(
        "aiTradingEvidenceValidation.productionEvidence.blockers.slice(0, 8)",
        1,
    )[1].split("aiTradingEvidenceValidation.items.some((item) => !item.ready)", 1)[0]
    validation_item_block = settings_source.split(
        "aiTradingEvidenceValidation.items.filter((item) => !item.ready)",
        1,
    )[1].split("</div>\n                            </div>", 1)[0]

    assert "aiTradingEvidenceExplain.productionEvidence.blockers.slice(0, 8)" in explain_root_block
    assert "formatAiTradingProductionEvidenceBlocker(blocker)" in explain_root_block
    assert "formatReadinessCode(blocker)" not in explain_root_block
    assert "formatAiTradingProductionEvidenceBlocker(blocker)" in explain_block
    assert "formatReadinessCode(blocker)" not in explain_block
    assert "formatAiTradingProductionEvidenceBlocker(blocker)" in validation_block
    assert "formatReadinessCode(blocker)" not in validation_block
    assert "item.blockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker).join(', ')" in validation_item_block
    assert "item.blockers.slice(0, 2).map(formatReadinessCode).join(', ')" not in validation_item_block


def test_admin_production_evidence_progress_ui_uses_safe_projection() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    progress_block = settings_source.split(
        "{t('settings.aiTradingEvidenceProgress', 'Evidence progress')}",
        1,
    )[1].split("{aiTradingEvidenceExplain.productionEvidence.blockers.length > 0", 1)[0]
    validation_progress_block = settings_source.split(
        "aiTradingEvidenceValidation.progress.pendingCount",
        1,
    )[1].split("aiTradingEvidenceValidation.productionEvidence.expiresAt", 1)[0]

    assert "progress.acceptedCount" in progress_block
    assert "progress.pendingCount" in progress_block
    assert "progress.blockedCount" in progress_block
    assert "progress.requiredCount" in progress_block
    assert "progress.liveOrderGateBlockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker)" in progress_block
    assert "progress.nextRequiredItemIds.slice(0, 4).map(formatProductionEvidenceItemName)" in progress_block
    assert "progress.nextRequiredActions.slice(0, 2).join(' | ')" in progress_block
    assert "progress.liveOrderGateBlockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker)" in validation_progress_block
    assert "progress.nextRequiredItemIds.slice(0, 3).map(formatProductionEvidenceItemName)" in validation_progress_block
    assert "progress.nextRequiredActions.slice(0, 2).join(' | ')" in validation_progress_block
    assert "formatReadinessCode" not in progress_block
    assert "formatReadinessCode" not in validation_progress_block
    assert "evidence_summary" not in progress_block
    assert "production_evidence_file" not in progress_block
    assert "secret_values_returned" not in progress_block
    assert "accepted_item_ids" in helper_source
    assert "pending_item_ids" in helper_source
    assert "blocked_item_ids" in helper_source
    assert "next_required_item_ids" in helper_source
    assert "next_required_actions" in helper_source
    assert "live_order_gate_blockers" in helper_source


def test_ai_trading_runtime_context_budget_ui_uses_counts_only_projection() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    budget_block = hyper_ai_source.split(
        "const aiTradingAgentContextBudget = aiTradingRuntime?.agent_sessions?.context_budget",
        1,
    )[1].split("const aiTradingAgentSessions = useMemo", 1)[0]
    sessions_card_block = hyper_ai_source.split(
        "{t('hyperAi.aiTradingSessions', 'Sessions')}",
        1,
    )[1].split("{t('hyperAi.aiTradingSpecs', 'Specs')}", 1)[0]

    assert "aiTradingAgentContextBudget?.near_budget_count" in budget_block
    assert "aiTradingAgentContextBudget?.redacted_context_summary_count" in budget_block
    assert "aiTradingAgentContextBudget?.sensitive_context_summary_count" in budget_block
    assert "aiTradingAgentContextBudget?.over_budget_count" in budget_block
    assert "aiTradingAgentContextBudget.max_context_summary_chars" in budget_block
    assert "aiTradingAgentContextBudget.context_summary_max_chars" in budget_block
    assert "aiTradingAgentContextBudgetLabel()" in sessions_card_block
    assert "aiTradingAgentContextBudgetTone" in sessions_card_block

    budget_block_without_allowed_count_fields = (
        budget_block
        .replace("redacted_context_summary_count", "")
        .replace("sensitive_context_summary_count", "")
        .replace("max_context_summary_chars", "")
        .replace("context_summary_max_chars", "")
    )
    assert "context_summary" not in budget_block_without_allowed_count_fields
    assert "context_summary" not in sessions_card_block


def test_ai_trading_gateway_mode_ui_uses_non_secret_runtime_projection() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    gateway_label_block = hyper_ai_source.split(
        "const gatewayTargetLabel = (): string => {",
        1,
    )[1].split("const modelAdjustmentBlockerLabel", 1)[0]
    gateway_card_block = hyper_ai_source.split(
        "{t('hyperAi.aiTradingGateway', 'Gateway')}",
        1,
    )[1].split("{t('hyperAi.aiTradingModel', 'Model')}", 1)[0]

    assert "aiTradingRuntime?.gateway?.mode" in gateway_label_block
    assert "aiTradingRuntime?.gateway?.target_kind" in gateway_label_block
    assert "production_gateway_mode_must_be_http_json" in hyper_ai_source
    assert "gatewayTargetLabel()" in gateway_card_block
    assert "AI_TRADING_SIGNAL_GATEWAY_TOKEN" not in hyper_ai_source
    assert "gateway?.url" not in gateway_label_block
    assert "gateway_url" not in gateway_label_block


def test_ai_trading_handoff_error_paths_use_safe_formatter() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    submit_block = hyper_ai_source.split(
        "const handleSubmitSignalEventHandoff = async",
        1,
    )[1].split("const handleInspectSignalHandoffAttempts = async", 1)[0]
    attempts_block = hyper_ai_source.split(
        "const handleInspectSignalHandoffAttempts = async",
        1,
    )[1].split("const handleRejectSignalEvent = async", 1)[0]
    reject_block = hyper_ai_source.split(
        "const handleRejectSignalEvent = async",
        1,
    )[1].split("const fetchConversations = async", 1)[0]

    assert "formatAiTradingSignalActionApiError" in hyper_ai_source
    assert "formatAiTradingSignalActionApiError" in helper_source
    assert "SIGNAL_ACTION_API_DETAIL_LABELS" in helper_source
    assert "SIGNAL_ACTION_API_STATUS_LABELS" in helper_source
    assert "safeSignalActionApiDetailLabel" in helper_source
    assert "Signal event is not eligible for handoff:" in helper_source
    assert "Signal gateway handoff failed:" in helper_source
    assert "production_handoff_approval_required" in helper_source
    assert "signal_event_stale_for_handoff" in helper_source
    assert "agent_session_archived" in helper_source

    for safe_error_block in (submit_block, attempts_block, reject_block):
        assert "formatAiTradingSignalActionApiError(res.status, data.detail, fallback)" in safe_error_block
        assert "formatAiTradingSignalActionApiError(0, null, fallback)" in safe_error_block
        assert "throw new Error(data.detail" not in safe_error_block
        assert "const detail = data.detail" not in safe_error_block
        assert "typeof detail === 'string'" not in safe_error_block
        assert "e instanceof Error ? e.message" not in safe_error_block


def test_ai_trading_strategy_action_error_paths_use_safe_formatter() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    strategy_actions_block = hyper_ai_source.split(
        "const handleStrategySpecDraft = async",
        1,
    )[1].split("const handleSubmitSignalEventHandoff = async", 1)[0]
    backtest_page_block = hyper_ai_source.split(
        "const loadBacktestEvidencePage = async",
        1,
    )[1].split("loadBacktestEvidencePage()", 1)[0]

    assert "formatAiTradingStrategyActionApiError" in hyper_ai_source
    assert "formatAiTradingStrategyActionApiError" in helper_source
    assert "STRATEGY_ACTION_API_DETAIL_LABELS" in helper_source
    assert "STRATEGY_ACTION_API_STATUS_LABELS" in helper_source
    assert "safeStrategyActionApiDetailLabel" in helper_source
    assert "Strategy spec not found" in helper_source
    assert "No handoff-ready matching Program Backtest result was found" in helper_source
    assert "DeepSeek/Qwen profile is not configured" in helper_source
    assert "Backtest preflight blocked:" in helper_source

    assert "formatAiTradingStrategyActionApiError(res.status, data.detail, fallback)" in strategy_actions_block
    assert "formatAiTradingStrategyActionApiError(0, null, fallback)" in strategy_actions_block
    assert "formatAiTradingStrategyActionApiError(attachRes.status, attachData.detail" in strategy_actions_block
    assert "formatAiTradingStrategyActionApiError(response.status, null" in strategy_actions_block
    assert "formatAiTradingStrategyActionApiError(res.status, data.detail, fallback)" in backtest_page_block
    assert "formatAiTradingStrategyActionApiError(0, null, fallback)" in backtest_page_block
    assert "aiTradingBacktestMetricsObjectRequired" in strategy_actions_block
    assert "aiTradingInvalidBacktestMetricsJson" in strategy_actions_block

    for safe_error_block in (strategy_actions_block, backtest_page_block):
        assert "throw new Error(data.detail" not in safe_error_block
        assert "throw new Error(attachData.detail" not in safe_error_block
        assert "throw new Error('Metrics must be a JSON object')" not in safe_error_block
        assert "data.detail ||" not in safe_error_block
        assert "attachData.detail ||" not in safe_error_block
        assert "response.text()" not in safe_error_block
        assert "event.message" not in safe_error_block
        assert "e instanceof Error ? e.message" not in safe_error_block
        assert "error instanceof Error ? error.message" not in safe_error_block


def test_ai_trading_backtest_summary_uses_inline_inputs_without_browser_prompt() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    backtest_summary_block = hyper_ai_source.split(
        "const handleAttachBacktestSummary = async",
        1,
    )[1].split("const handleAttachProgramBacktestResult = async", 1)[0]
    recent_specs_block = hyper_ai_source.split(
        "{recentStrategySpecs.map(record =>",
        1,
    )[1].split("onClick={() => handleAttachProgramBacktestResult(record.id)}", 1)[0]

    assert "window.prompt" not in backtest_summary_block
    assert "strategyBacktestSummaryId.trim()" in backtest_summary_block
    assert "strategyBacktestSummaryMetricsText.trim()" in backtest_summary_block
    assert "setStrategyDraftRecord(inlineRecord)" in backtest_summary_block
    assert "setStrategyDraft(inlineRecord.spec)" in backtest_summary_block
    assert "handleAttachBacktestSummary(record.id, record)" in recent_specs_block


def test_ai_trading_program_backtest_result_uses_inline_input_without_browser_prompt() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    program_backtest_block = hyper_ai_source.split(
        "const handleAttachProgramBacktestResult = async",
        1,
    )[1].split("const handleAttachLatestProgramBacktestResult = async", 1)[0]
    current_strategy_inputs_block = hyper_ai_source.split(
        'data-testid="ai-trading-program-backtest-result-id"',
        1,
    )[1].split('data-testid="ai-trading-backtest-summary-metrics"', 1)[0]
    recent_specs_block = hyper_ai_source.split(
        "{recentStrategySpecs.map(record =>",
        1,
    )[1].split("onClick={() => handleAttachLatestProgramBacktestResult(record.id)}", 1)[0]

    assert "window.prompt" not in program_backtest_block
    assert "strategyProgramBacktestResultId.trim()" in program_backtest_block
    assert "setStrategyDraftRecord(inlineRecord)" in program_backtest_block
    assert "setStrategyDraft(inlineRecord.spec)" in program_backtest_block
    assert "setStrategyProgramBacktestResultId('')" in program_backtest_block
    assert "strategyProgramBacktestResultId" in current_strategy_inputs_block
    assert "inputMode=\"numeric\"" in current_strategy_inputs_block
    assert "handleAttachProgramBacktestResult(record.id, undefined, record)" in recent_specs_block


def test_ai_trading_program_backtest_run_uses_inline_confirmation_without_browser_confirm() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    program_backtest_run_block = hyper_ai_source.split(
        "const handleRunStrategyProgramBacktest = async",
        1,
    )[1].split("const handleInspectStrategyBacktestEvidence = async", 1)[0]
    program_backtest_preflight_block = hyper_ai_source.split(
        "const handleStrategyBacktestPreflight = async",
        1,
    )[1].split("const handleRunStrategyProgramBacktest = async", 1)[0]
    current_strategy_controls_block = hyper_ai_source.split(
        'data-testid="ai-trading-program-backtest-run-confirm"',
        1,
    )[1].split("strategyBacktestRunStatus && strategyBacktestRunStatus.specId", 1)[0]
    recent_specs_block = hyper_ai_source.split(
        "{recentStrategySpecs.map(record =>",
        1,
    )[1].split("onClick={() => handleInspectStrategyBacktestEvidence(record.id)}", 1)[0]

    assert "window.confirm" not in program_backtest_run_block
    assert "strategyProgramBacktestRunConfirmed" in program_backtest_run_block
    assert "aiTradingRunBacktestConfirmRequired" in program_backtest_run_block
    assert "setStrategyProgramBacktestRunConfirmed(false)" in program_backtest_run_block
    assert "strategyProgramBacktestRunConfirmed" not in program_backtest_preflight_block
    assert "strategyProgramBacktestRunConfirmed" in current_strategy_controls_block
    assert "ai-trading-program-backtest-run-confirm" in hyper_ai_source
    assert "!strategyProgramBacktestRunConfirmed" in current_strategy_controls_block
    assert "!strategyProgramBacktestRunConfirmed" in recent_specs_block


def test_ai_trading_signal_handoff_uses_inline_confirmation_without_browser_confirm() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    signal_handoff_block = hyper_ai_source.split(
        "const handleSubmitSignalEventHandoff = async",
        1,
    )[1].split("const handleInspectSignalHandoffAttempts = async", 1)[0]
    recent_signals_block = hyper_ai_source.split(
        "{recentSignalEvents.map(event =>",
        1,
    )[1].split("{/* Memory Entry */}", 1)[0]

    assert "window.confirm" not in signal_handoff_block
    assert "signalHandoffConfirmedEventIds[eventId]" in signal_handoff_block
    assert "aiTradingSignalHandoffConfirmRequired" in signal_handoff_block
    assert "confirmed_by_user: true" in signal_handoff_block
    assert "confirmation_source: 'hyper_ai_recent_signal_panel'" in signal_handoff_block
    assert "setSignalHandoffEventConfirmed(eventId, false)" in signal_handoff_block
    assert 'data-testid="ai-trading-signal-handoff-confirm"' in recent_signals_block
    assert "setSignalHandoffEventConfirmed(event.id, checked === true)" in recent_signals_block
    assert "!signalHandoffConfirmedEventIds[event.id]" in recent_signals_block
    assert "aiTradingSignalHandoffConfirmRequired" in hyper_ai_source


def test_ai_trading_agent_session_archive_uses_inline_confirmation_without_browser_confirm() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    archive_session_block = hyper_ai_source.split(
        "const handleArchiveAgentSession = async",
        1,
    )[1].split("const handleSaveStrategyDraft = async", 1)[0]
    session_controls_block = hyper_ai_source.split(
        "onClick={handleArchiveAgentSession}",
        1,
    )[1].split('value={agentSessionSummaryDraft}', 1)[0]

    assert "window.confirm" not in archive_session_block
    assert "agentSessionArchiveConfirmed" in archive_session_block
    assert "aiTradingArchiveSessionConfirmRequired" in archive_session_block
    assert "setAgentSessionArchiveConfirmed(false)" in archive_session_block
    assert 'data-testid="ai-trading-agent-session-archive-confirm"' in hyper_ai_source
    assert "setAgentSessionArchiveConfirmed(checked === true)" in session_controls_block
    assert "!agentSessionArchiveConfirmed" in session_controls_block
    assert "aiTradingArchiveSessionConfirmInline" in session_controls_block


def test_ai_trading_hyperliquid_wallet_delete_uses_inline_confirmation_without_browser_confirm() -> None:
    one_click_source = HYPERLIQUID_WALLET_SECTION.read_text(encoding="utf-8")
    manual_source = WALLET_CONFIG_PANEL.read_text(encoding="utf-8")
    one_click_delete_block = one_click_source.split(
        "const handleDeleteWallet = async",
        1,
    )[1].split("const renderSetupProgress", 1)[0]
    one_click_controls_block = one_click_source.split(
        'data-testid="hyperliquid-wallet-delete-confirm"',
        1,
    )[1].split("wallet.testConnection", 1)[0]
    manual_delete_block = manual_source.split(
        "const handleDeleteWallet = async",
        1,
    )[1].split("const renderWalletBlock", 1)[0]
    manual_controls_block = manual_source.split(
        'data-testid="manual-hyperliquid-wallet-delete-confirm"',
        1,
    )[1].split("wallet.testConnection", 1)[0]

    for delete_block in (one_click_delete_block, manual_delete_block):
        assert "window.confirm" not in delete_block
        assert "confirm(" not in delete_block
        assert "deleteWalletConfirmed[environment]" in delete_block
        assert "wallet.delete.confirmRequired" in delete_block
        assert "setWalletDeleteConfirmed(environment, false)" in delete_block

    for controls_block in (one_click_controls_block, manual_controls_block):
        assert "setWalletDeleteConfirmed(environment, checked === true)" in controls_block
        assert "wallet.delete.confirmInline" in controls_block

    assert "disabled={loading || !deleteWalletConfirmed[environment]}" in one_click_source
    assert "disabled={loading || !deleteWalletConfirmed[environment]}" in manual_source


def test_ai_trading_binance_wallet_delete_uses_inline_confirmation_without_browser_confirm() -> None:
    binance_source = BINANCE_WALLET_SECTION.read_text(encoding="utf-8")
    delete_block = binance_source.split(
        "const handleDeleteWallet = async",
        1,
    )[1].split("const renderWalletBlock", 1)[0]
    controls_block = binance_source.split(
        'data-testid="binance-wallet-delete-confirm"',
        1,
    )[1].split("wallet.testConnection", 1)[0]

    assert "window.confirm" not in delete_block
    assert "confirm(" not in delete_block
    assert "deleteWalletConfirmed[environment]" in delete_block
    assert "wallet.delete.confirmRequired" in delete_block
    assert "setWalletDeleteConfirmed(environment, false)" in delete_block
    assert "setWalletDeleteConfirmed(environment, checked === true)" in controls_block
    assert "wallet.delete.confirmInline" in controls_block
    assert "disabled={saving || !deleteWalletConfirmed[environment]}" in binance_source


def test_ai_trading_agent_session_error_paths_use_safe_formatter() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    detail_page_block = hyper_ai_source.split(
        "const loadAgentSessionDetailPage = async",
        1,
    )[1].split("loadAgentSessionDetailPage()", 1)[0]
    detail_compress_block = hyper_ai_source.split(
        "const handleCompressAgentSessionDetailContext = async",
        1,
    )[1].split("const fetchBotConfig", 1)[0]
    context_load_block = hyper_ai_source.split(
        "const fetchAiTradingAgentSessionContext = async",
        1,
    )[1].split("const handleCompressAgentSessionContext = async", 1)[0]
    context_compress_block = hyper_ai_source.split(
        "const handleCompressAgentSessionContext = async",
        1,
    )[1].split("useEffect(() => {\n    fetchAiTradingRecords()", 1)[0]
    save_block = hyper_ai_source.split(
        "const handleSaveAgentSession = async",
        1,
    )[1].split("const handleArchiveAgentSession = async", 1)[0]
    archive_block = hyper_ai_source.split(
        "const handleArchiveAgentSession = async",
        1,
    )[1].split("const handleTradingSymbolGroupChange", 1)[0]

    assert "formatAiTradingAgentSessionApiError" in hyper_ai_source
    assert "formatAiTradingAgentSessionApiError" in helper_source
    assert "AGENT_SESSION_API_DETAIL_LABELS" in helper_source
    assert "AGENT_SESSION_API_STATUS_LABELS" in helper_source
    assert "safeAgentSessionApiDetailLabel" in helper_source
    assert "AI Trading agent session not found" in helper_source
    assert "Agent session not found" in helper_source
    assert "'context_' + 'summary must not contain'" in helper_source
    assert "Context summary contains sensitive text" in helper_source

    for safe_error_block in (
        detail_page_block,
        detail_compress_block,
        context_load_block,
        context_compress_block,
        save_block,
        archive_block,
    ):
        assert "formatAiTradingAgentSessionApiError(res.status, data.detail, fallback)" in safe_error_block
        assert "formatAiTradingAgentSessionApiError(0, null, fallback)" in safe_error_block
        assert "throw new Error(data.detail" not in safe_error_block
        assert "data.detail ||" not in safe_error_block
        assert "e instanceof Error ? e.message" not in safe_error_block


def test_ai_trading_session_context_prompt_uses_defensive_sanitizer() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    context_load_block = hyper_ai_source.split(
        "const fetchAiTradingAgentSessionContext = async",
        1,
    )[1].split("const handleCompressAgentSessionContext = async", 1)[0]

    assert "sanitizeAiTradingAgentSessionContextForPrompt" in hyper_ai_source
    assert "AI_TRADING_CONTEXT_SUMMARY_KEY_PATTERN" in hyper_ai_source
    assert "authorization|bearer" in hyper_ai_source
    assert "const promptContext = sanitizeAiTradingAgentSessionContextForPrompt(context)" in context_load_block
    assert "JSON.stringify(promptContext, null, 2)" in context_load_block
    assert "JSON.stringify(context, null, 2)" not in context_load_block


def test_ai_trading_review_prompt_packets_use_defensive_sanitizer() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    review_prompt_block = hyper_ai_source.split(
        "const handleStrategySpecDraft = async",
        1,
    )[1].split("const fetchConversations = async", 1)[0]

    assert "function sanitizeAiTradingPromptPacket" in hyper_ai_source
    assert "AI_TRADING_PROMPT_TEXT_KEY_PATTERN" in hyper_ai_source
    assert "AI_TRADING_PROMPT_TEXT_SENSITIVE_PATTERN" in hyper_ai_source
    assert "[redacted_sensitive_text]" in hyper_ai_source

    for raw_snippet in (
        "JSON.stringify(spec, null, 2)",
        "JSON.stringify(reviewPacket, null, 2)",
        "JSON.stringify(record.spec?.backtest || {}, null, 2)",
        "JSON.stringify(backtest, null, 2)",
        "JSON.stringify(preflight, null, 2)",
        "JSON.stringify({ result: completePayload, attached_backtest: attachedBacktest }, null, 2)",
        "JSON.stringify(evidence, null, 2)",
        "JSON.stringify(signalPreview, null, 2)",
        "JSON.stringify(signal, null, 2)",
        "JSON.stringify(event, null, 2)",
        "JSON.stringify({ signal_event_id: eventId, attempts }, null, 2)",
    ):
        assert raw_snippet not in review_prompt_block

    for safe_snippet in (
        "JSON.stringify(sanitizeAiTradingPromptPacket(spec), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(reviewPacket), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(record.spec?.backtest || {}), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(backtest), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(preflight), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket({ result: completePayload, attached_backtest: attachedBacktest }), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(evidence), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(signalPreview), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(signal), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket(event), null, 2)",
        "JSON.stringify(sanitizeAiTradingPromptPacket({ signal_event_id: eventId, attempts }), null, 2)",
    ):
        assert safe_snippet in review_prompt_block


def test_ai_trading_model_adjust_output_safety_is_visible_in_frontend() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    model_adjust_block = hyper_ai_source.split(
        "const handleModelAdjustStrategyDraft = async",
        1,
    )[1].split("const handleAttachBacktestSummary = async", 1)[0]
    current_strategy_safety_block = hyper_ai_source.split(
        'data-testid="ai-trading-model-output-safety-warning"',
        1,
    )[1].split("{currentStrategyActionBlockedByArchivedSession", 1)[0]

    assert "AI_TRADING_MODEL_OUTPUT_SENSITIVE_WARNING" in hyper_ai_source
    assert "AI_TRADING_MODEL_OUTPUT_DIRECT_ORDER_WARNING" in hyper_ai_source
    assert "model_output_sensitive_text_redacted" in hyper_ai_source
    assert "model_output_direct_order_intent_ignored" in hyper_ai_source
    assert "currentStrategyModelOutputSafetyLabels" in hyper_ai_source
    assert "model_output_safety" in model_adjust_block
    assert "AI_TRADING_MODEL_OUTPUT_SAFETY_WARNINGS" in model_adjust_block
    assert "sensitive_text_redacted" in model_adjust_block
    assert "direct_order_intent_ignored" in model_adjust_block
    assert "validation_warnings" in model_adjust_block
    assert "currentStrategyModelOutputSafetyLabels.join" in current_strategy_safety_block
    assert "aiTradingModelOutputSensitiveRedacted" in hyper_ai_source
    assert "aiTradingModelOutputDirectOrderIgnored" in hyper_ai_source


def test_ai_trading_model_adjustment_readiness_ui_uses_safe_blocker_labels() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    model_readiness_helper_block = hyper_ai_source.split(
        "const modelAdjustmentBlockerLabel =",
        1,
    )[1].split("const aiTradingValidationWarningLabel", 1)[0]
    model_runtime_card_block = hyper_ai_source.split(
        "{t('hyperAi.aiTradingModel', 'Model')}",
        1,
    )[1].split("{t('hyperAi.aiTradingSessions', 'Sessions')}", 1)[0]
    model_adjust_button_block = hyper_ai_source.split(
        "onClick={handleModelAdjustStrategyDraft}",
        1,
    )[1].split("{strategyModelAdjusting ?", 1)[0]
    model_config_saved_block = hyper_ai_source.split(
        "const handleLLMConfigSaved = () => {",
        1,
    )[1].split("const fetchAiTradingAgentSessionContext", 1)[0]
    llm_config_modal_block = hyper_ai_source.split(
        "<LLMConfigModal",
        1,
    )[1].split("<MemoryModal", 1)[0]

    assert "model_profile_not_configured" in model_readiness_helper_block
    assert "model_profile_credential_missing" in model_readiness_helper_block
    assert "model_profile_credential_unreadable" in model_readiness_helper_block
    assert "model_provider_not_deepseek_or_qwen" in model_readiness_helper_block
    assert "model_name_missing" in model_readiness_helper_block
    assert "model_base_url_missing" in model_readiness_helper_block
    assert "next_actions?: string[]" in hyper_ai_source
    assert "aiTradingModelAdjustmentNextActions" in model_readiness_helper_block
    assert "modelAdjustmentNextActionSummary()" in model_readiness_helper_block
    assert "modelAdjustmentReadinessDetailLabel()" in model_runtime_card_block
    assert "modelAdjustmentUnavailableTitle()" in model_adjust_button_block
    assert "Model adjustment blocked: {{summary}}" in hyper_ai_source
    assert 'data-testid="ai-trading-model-config-button"' in model_runtime_card_block
    assert "setShowConfigModal(true)" in model_runtime_card_block
    assert "Configure DeepSeek/Qwen model" in model_runtime_card_block
    assert "fetchProfile()" in model_config_saved_block
    assert "refreshAiTradingState()" in model_config_saved_block
    assert "onSaved={handleLLMConfigSaved}" in llm_config_modal_block

    safe_ui_blocks = model_runtime_card_block + model_adjust_button_block
    assert "llm_api_key" not in safe_ui_blocks
    assert "llm_base_url" not in safe_ui_blocks
    assert "api_key" not in safe_ui_blocks
    assert "base_url" not in safe_ui_blocks


def test_ai_trading_model_config_modal_uses_safe_api_error_formatter() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    modal_block = hyper_ai_source.split(
        "function LLMConfigModal",
        1,
    )[1].split("if (!open) return null", 1)[0]

    assert "formatAiTradingModelConfigApiError" in hyper_ai_source
    assert "formatAiTradingModelConfigApiError" in helper_source
    assert "MODEL_CONFIG_API_DETAIL_LABELS" in helper_source
    assert "MODEL_CONFIG_API_STATUS_LABELS" in helper_source
    assert "Unknown provider:" in helper_source
    assert "Connection failed:" in helper_source
    assert "Model provider connection failed" in helper_source

    assert "formatAiTradingModelConfigApiError(res.status, data.detail, fallback)" in modal_block
    assert "formatAiTradingModelConfigApiError(0, null, fallback)" in modal_block
    assert "throw new Error(errData.detail" not in modal_block
    assert "errData.detail ||" not in modal_block
    assert "setError(e.message" not in modal_block
    assert "setError(e instanceof Error ? e.message" not in modal_block


def test_hyper_ai_onboarding_uses_safe_model_and_stream_errors() -> None:
    source = HYPER_AI_ONBOARDING.read_text(encoding="utf-8")
    config_block = source.split(
        "const handleTestAndContinue = async () => {",
        1,
    )[1].split("  // Render based on current step", 1)[0]
    stream_block = source.split(
        "const pollStreamResponse = async (taskId: string) => {",
        1,
    )[1].split("  const handleKeyDown", 1)[0]

    assert "formatAiTradingModelConfigApiError" in source
    assert "const data = await saveRes.json().catch(() => ({}))" in config_block
    assert "setError(formatAiTradingModelConfigApiError(saveRes.status, data.detail, fallback))" in config_block
    assert "setError(formatAiTradingModelConfigApiError(0, null, fallback))" in config_block
    assert "throw new Error(errData.detail" not in config_block
    assert "errData.detail ||" not in config_block
    assert "setError(e.message" not in config_block
    assert "catch (e: any)" not in config_block

    assert "throw new Error(t('hyperAi.onboarding.streamError', 'Stream error'))" in stream_block
    assert "chunk.data?.message || 'Stream error'" not in stream_block


def test_root_app_has_error_boundary_for_onboarding_skip_blank_page() -> None:
    main_source = FRONTEND_MAIN.read_text(encoding="utf-8")
    boundary_source = APP_ERROR_BOUNDARY.read_text(encoding="utf-8")
    render_block = main_source.split(
        "ReactDOM.createRoot(document.getElementById('root')!).render(",
        1,
    )[1]

    assert "import AppErrorBoundary from '@/components/layout/AppErrorBoundary'" in main_source
    assert "<AppErrorBoundary>" in render_block
    assert "<AuthProvider>" in render_block
    assert render_block.index("<AppErrorBoundary>") < render_block.index("<AuthProvider>")
    assert "static getDerivedStateFromError" in boundary_source
    assert "componentDidCatch" in boundary_source
    assert "window.location.reload()" in boundary_source
    assert "The app recovered from a UI loading error" in boundary_source
    assert "HyperAlpha UI render failure" in boundary_source
    assert "{String(error)}" not in boundary_source
    assert "{error.message}" not in boundary_source
    assert "{this.state.error" not in boundary_source


def test_hyper_ai_model_config_is_nonblocking_after_splash() -> None:
    main_source = FRONTEND_MAIN.read_text(encoding="utf-8")
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    app_block = main_source.split("function App()", 1)[1].split(
        "const renderMainContent = () => {",
        1,
    )[0]

    assert "HyperAiOnboarding" not in main_source
    assert "showOnboarding" not in main_source
    assert "checkHyperAiConfig" not in main_source
    assert "llm_configured" not in app_block
    assert "missing config must not block app entry" in main_source
    assert "setShowSplash(false)" in app_block

    assert "data-testid=\"ai-trading-model-config-button\"" in hyper_ai_source
    assert "onClick={() => setShowConfigModal(true)}" in hyper_ai_source
    assert "<LLMConfigModal" in hyper_ai_source
    assert "Configure DeepSeek/Qwen model" in hyper_ai_source


def test_hyper_ai_agent_session_route_id_rejects_sensitive_values_source_guard() -> None:
    source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    cleaner_block = source.split("function cleanAiTradingAgentSessionRouteId", 1)[1].split(
        "function sanitizeAiTradingSymbolText",
        1,
    )[0]
    parser_block = source.split("function parseAiTradingAgentSessionRouteId", 1)[1].split(
        "function asRecord",
        1,
    )[0]
    open_detail_block = source.split("const handleOpenAgentSessionDetailPage", 1)[1].split(
        "const handleCompressAgentSessionDetailContext",
        1,
    )[0]

    assert "AI_TRADING_AGENT_SESSION_ID_SENSITIVE_PATTERN" in source
    assert "api[_-]?key|authorization|bearer|token|secret|private[_-]?key|password" in source
    assert "AI_TRADING_AGENT_SESSION_ID_SENSITIVE_PATTERN.test(trimmed)" in cleaner_block
    assert "return null" in cleaner_block.split("AI_TRADING_AGENT_SESSION_ID_SENSITIVE_PATTERN.test(trimmed)", 1)[1].split(
        "return /^[A-Za-z0-9]",
        1,
    )[0]
    assert "cleanAiTradingAgentSessionRouteId(pathMatch?.[1])" in parser_block
    assert "cleanAiTradingAgentSessionRouteId(params.get('agentSessionId')" in parser_block
    assert "cleanAiTradingAgentSessionRouteId(agentSessionId || selectedAiTradingAgentSession?.id)" in open_detail_block
    assert "encodeURIComponent(targetSessionId)" in open_detail_block


def test_frontend_public_asset_paths_do_not_use_static_prefix() -> None:
    frontend_root = REPO_ROOT / "frontend"
    source_files = [frontend_root / "index.html"]
    for pattern in ("*.ts", "*.tsx"):
        source_files.extend((frontend_root / "app").rglob(pattern))

    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in source_files
        if "/static/" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_contact_dialog_forwards_trigger_ref_to_avoid_radix_blank_page_noise() -> None:
    source = CONTACT_DIALOG.read_text(encoding="utf-8")

    assert "React.forwardRef<HTMLElement, ContactDialogProps>" in source
    assert "React.cloneElement(children, { ...triggerProps, ref }" in source
    assert "<DialogTrigger asChild>{trigger}</DialogTrigger>" in source
    assert "ContactDialog.displayName = 'ContactDialog'" in source


def test_hyper_ai_bot_and_tool_config_errors_use_safe_labels() -> None:
    bot_source = BOT_INTEGRATION_MODAL.read_text(encoding="utf-8")
    tool_source = TOOL_CONFIG_MODAL.read_text(encoding="utf-8")

    assert "formatBotIntegrationConnectError" in bot_source
    assert "connectAuthRequired" in bot_source
    assert "connectAccessDenied" in bot_source
    assert "connectRateLimited" in bot_source
    assert "connectUnavailable" in bot_source
    assert "const data = await res.json().catch(() => ({}))" in bot_source
    assert "setError(formatBotIntegrationConnectError(res.status))" in bot_source
    assert "setError(formatBotIntegrationConnectError(0))" in bot_source
    assert "setError(data.detail || 'Connection failed')" not in bot_source
    assert "err instanceof Error ? err.message" not in bot_source

    assert "formatToolConfigSaveError" in tool_source
    assert "formatToolConfigRemoveError" in tool_source
    assert "configAuthRequired" in tool_source
    assert "configAccessDenied" in tool_source
    assert "removeAccessDenied" in tool_source
    assert "const data = await res.json().catch(() => ({}))" in tool_source
    assert "setError(formatToolConfigSaveError(res.status))" in tool_source
    assert "setError(formatToolConfigSaveError(0))" in tool_source
    assert "setError(formatToolConfigRemoveError(res.status))" in tool_source
    assert "setError(formatToolConfigRemoveError(0))" in tool_source
    assert "setError(data.error || data.detail || 'Save failed')" not in tool_source
    assert "setError(err instanceof Error ? err.message : 'Save failed')" not in tool_source
    assert "setError('Remove failed')" not in tool_source


def test_ai_trading_market_universe_loader_uses_safe_api_error_formatter() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    helper_source = READINESS_HELPER.read_text(encoding="utf-8")
    loader_block = hyper_ai_source.split(
        "const fetchTradingSymbols = async () => {",
        1,
    )[1].split("const fetchAiTradingRuntime = async () => {", 1)[0]

    assert "formatAiTradingMarketUniverseApiError" in hyper_ai_source
    assert "formatAiTradingMarketUniverseApiError" in helper_source
    assert "MARKET_UNIVERSE_API_DETAIL_LABELS" in helper_source
    assert "MARKET_UNIVERSE_API_STATUS_LABELS" in helper_source
    assert "Trading-symbol service is unavailable" in helper_source
    assert "Trading-symbol upstream is unavailable" in helper_source

    assert "allSymbolSourcesFailed" in loader_block
    assert "formatAiTradingMarketUniverseApiError(error.status, error.detail, fallback)" in loader_block
    assert "formatAiTradingMarketUniverseApiError(0, null, fallback)" in loader_block
    assert "setTradingSymbolsError(e instanceof Error ? e.message" not in loader_block
    assert "setTradingSymbolsError(error instanceof Error ? error.message" not in loader_block
    assert "data.detail ||" not in loader_block
    assert "errData.detail ||" not in loader_block


def test_ai_trading_market_symbols_are_sanitized_before_ui_prompt_and_draft() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    loader_block = hyper_ai_source.split(
        "const fetchTradingSymbols = async () => {",
        1,
    )[1].split("const fetchAiTradingRuntime = async () => {", 1)[0]
    prompt_block = hyper_ai_source.split(
        "const handleTradingSymbolPrompt = (symbol: string) => {",
        1,
    )[1].split("const handleStrategySpecDraft = async", 1)[0]
    draft_block = hyper_ai_source.split(
        "const handleStrategySpecDraft = async",
        1,
    )[1].split("const persistStrategyDraft = async", 1)[0]

    assert "function sanitizeAiTradingSymbolText" in hyper_ai_source
    assert "AI_TRADING_SYMBOL_TEXT_PATTERN" in hyper_ai_source
    assert "AI_TRADING_EXCHANGE_SYMBOL_TEXT_PATTERN" in hyper_ai_source
    assert "AI_TRADING_SYMBOL_SENSITIVE_PATTERN" in hyper_ai_source
    assert "api[_-]?key|authorization|bearer|token|secret|private[_-]?key|password" in hyper_ai_source
    assert ".map(sanitizeAiTradingSymbolText)" in loader_block
    assert "const safeSymbol = sanitizeAiTradingSymbolText(symbol)" in prompt_block
    assert "${safeSymbol}" in prompt_block
    assert "const safeSymbol = sanitizeAiTradingSymbolText(symbol)" in draft_block
    assert "${safeSymbol}" in draft_block
    assert "symbol: safeSymbol" in draft_block
    assert "setStrategyDraftLoadingSymbol(safeSymbol)" in draft_block
    assert "for ${symbol}" not in prompt_block
    assert "针对 ${symbol}" not in prompt_block
    assert "for ${symbol}" not in draft_block
    assert "为 ${symbol}" not in draft_block
    assert "symbol," not in draft_block


def test_ai_trading_session_detail_validation_warnings_use_readable_labels() -> None:
    hyper_ai_source = HYPER_AI_PAGE.read_text(encoding="utf-8")
    session_detail_specs_block = hyper_ai_source.split(
        "agentSessionDetailSpecs.map",
        1,
    )[1].split("agentSessionDetailSpecs.length === 0", 1)[0]

    assert "aiTradingValidationWarningLabel" in hyper_ai_source
    assert "validationWarnings" in session_detail_specs_block
    assert "validationWarnings.slice(0, 3).map(aiTradingValidationWarningLabel).join" in session_detail_specs_block
    assert "(asRecord(spec.validation).warnings as unknown[]).slice(0, 3).map(String).join" not in session_detail_specs_block
