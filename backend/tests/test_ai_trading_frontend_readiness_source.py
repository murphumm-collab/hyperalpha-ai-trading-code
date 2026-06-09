from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PAGE = REPO_ROOT / "frontend" / "app" / "components" / "settings" / "SettingsPage.tsx"
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
