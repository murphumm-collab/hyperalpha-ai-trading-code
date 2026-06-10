from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PAGE = REPO_ROOT / "frontend" / "app" / "components" / "settings" / "SettingsPage.tsx"
HYPER_AI_PAGE = REPO_ROOT / "frontend" / "app" / "components" / "hyper-ai" / "HyperAiPage.tsx"
READINESS_HELPER = REPO_ROOT / "frontend" / "app" / "lib" / "aiTradingReadiness.ts"


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


def test_admin_production_evidence_validate_ui_uses_safe_projection() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")

    assert "/api/ai-trading/admin/production-evidence-template" in settings_source
    assert "/api/ai-trading/admin/production-evidence-validate" in settings_source
    assert "loadAiTradingEvidenceTemplate" in settings_source
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
    assert "external_evidence_item_blocked:" in helper_source
    assert "external_evidence_summary_missing_required_term:" in helper_source

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

    assert "formatAiTradingProductionEvidenceBlocker(blocker)" in explain_block
    assert "formatReadinessCode(blocker)" not in explain_block
    assert "formatAiTradingProductionEvidenceBlocker(blocker)" in validation_block
    assert "formatReadinessCode(blocker)" not in validation_block
    assert "item.blockers.slice(0, 2).map(formatAiTradingProductionEvidenceBlocker).join(', ')" in validation_item_block
    assert "item.blockers.slice(0, 2).map(formatReadinessCode).join(', ')" not in validation_item_block


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
