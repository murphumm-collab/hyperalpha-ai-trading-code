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

    assert "/api/ai-trading/admin/production-evidence-explain" in settings_source
    assert "extractAiTradingProductionEvidenceExplain" in settings_source
    assert "AiTradingProductionEvidenceExplainView" in settings_source
    assert "productionEvidence.acceptedCount" in settings_source
    assert "readyForLiveOrders" in settings_source
    assert "artifactRefCount" in settings_source
    assert "operatorGuidance" in settings_source
    assert "production_evidence_file" not in settings_source
    assert "AI_TRADING_SIGNAL_GATEWAY_TOKEN" not in settings_source
    assert "DEEPSEEK_API_KEY" not in settings_source
    assert "QWEN_API_KEY" not in settings_source
    assert "DASHSCOPE_API_KEY" not in settings_source

    assert "production_evidence" in helper_source
    assert "ready_for_live_orders" in helper_source
    assert "artifact_ref_count" in helper_source
    assert "operator_guidance" in helper_source
    assert "secret_values_returned" not in helper_source
    assert "production_evidence_file" not in helper_source


def test_admin_production_evidence_validate_ui_uses_safe_projection() -> None:
    settings_source = SETTINGS_PAGE.read_text(encoding="utf-8")

    assert "/api/ai-trading/admin/production-evidence-validate" in settings_source
    assert "aiTradingEvidenceValidationJson" in settings_source
    assert "aiTradingEvidenceValidation.productionEvidence.acceptedCount" in settings_source
    assert "aiTradingEvidenceValidation.readyForLiveOrders" in settings_source
    assert "extractAiTradingProductionEvidenceExplain(data.validation)" in settings_source
    assert "production_evidence_file" not in settings_source
    assert "AI_TRADING_SIGNAL_GATEWAY_TOKEN" not in settings_source
    assert "DEEPSEEK_API_KEY" not in settings_source
    assert "QWEN_API_KEY" not in settings_source
    assert "DASHSCOPE_API_KEY" not in settings_source


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
