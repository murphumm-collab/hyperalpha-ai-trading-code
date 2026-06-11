import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_trading_production_handoff_check.py"
SPEC = importlib.util.spec_from_file_location("ai_trading_production_handoff_check", SCRIPT_PATH)
production_check = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(production_check)


def _base_env(**overrides):
    env = {
        "AI_TRADING_SIGNAL_GATEWAY_ENABLED": "true",
        "AI_TRADING_SIGNAL_GATEWAY_URL": "https://orders.hyperalpha.org/api/ai-trading/signals",
        "AI_TRADING_SIGNAL_GATEWAY_TOKEN": "secret-token-value",
        "AI_TRADING_SIGNAL_GATEWAY_TIMEOUT_SECONDS": "10",
        "AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS": "300",
        "AI_TRADING_PRODUCTION_HANDOFF_APPROVED": "true",
    }
    env.update(overrides)
    return env


def test_local_mock_gateway_is_never_production_ready():
    report = production_check.build_report(
        _base_env(
            AI_TRADING_SIGNAL_GATEWAY_URL="http://127.0.0.1:5621/api/ai-trading/signals",
        )
    )

    assert report["production_handoff_ready"] is False
    assert "signal_gateway_url_must_be_https" in report["blockers"]
    assert "signal_gateway_url_must_not_be_local_or_private" in report["blockers"]
    assert "signal_gateway_url_must_not_be_mock_gateway" in report["blockers"]
    assert report["checks"]["token_value_returned"] is False


def test_placeholder_url_missing_token_and_approval_are_blocked():
    report = production_check.build_report(
        _base_env(
            AI_TRADING_SIGNAL_GATEWAY_URL="https://order-backend.example.com/api/ai-trading/signals",
            AI_TRADING_SIGNAL_GATEWAY_TOKEN="",
            AI_TRADING_PRODUCTION_HANDOFF_APPROVED="false",
        )
    )

    assert report["production_handoff_ready"] is False
    assert "signal_gateway_url_must_not_be_placeholder" in report["blockers"]
    assert "signal_gateway_token_missing" in report["blockers"]
    assert "production_handoff_approval_flag_missing" in report["blockers"]


def test_non_http_gateway_mode_is_blocked_without_leaking_token_value():
    report = production_check.build_report(
        _base_env(
            AI_TRADING_SIGNAL_GATEWAY_MODE="rabbitmq",
        )
    )

    assert report["production_handoff_ready"] is False
    assert "signal_gateway_mode_must_be_http_json" in report["blockers"]
    assert report["checks"]["gateway_mode"] == "rabbitmq"
    assert report["checks"]["supported_gateway_modes"] == ["http"]
    assert report["checks"]["token_value_returned"] is False
    assert "secret-token-value" not in str(report)


def test_private_network_https_gateway_is_blocked():
    report = production_check.build_report(
        _base_env(
            AI_TRADING_SIGNAL_GATEWAY_URL="https://10.0.0.8/api/ai-trading/signals",
        )
    )

    assert report["production_handoff_ready"] is False
    assert "signal_gateway_url_must_not_be_local_or_private" in report["blockers"]


def test_secret_like_gateway_host_is_blocked_and_redacted():
    secret_host = "secret-order-token-123456789.orders.hyperalpha.org"
    report = production_check.build_report(
        _base_env(
            AI_TRADING_SIGNAL_GATEWAY_URL=f"https://{secret_host}/api/ai-trading/signals",
        )
    )

    assert report["production_handoff_ready"] is False
    assert "signal_gateway_url_host_secret_pattern_detected" in report["blockers"]
    assert report["checks"]["gateway_url"]["host"] == "[redacted_sensitive_url_host]"
    assert report["checks"]["gateway_url"]["host_secret_pattern_detected"] is True
    serialized = str(report)
    assert secret_host not in serialized
    assert "secret-order-token-123456789" not in serialized


def test_ready_report_never_returns_secret_token_value():
    report = production_check.build_report(_base_env())

    assert report["production_handoff_ready"] is True
    assert report["blockers"] == []
    assert report["checks"]["token_present"] is True
    assert report["checks"]["token_value_returned"] is False
    assert "secret-token-value" not in str(report)


def test_env_file_parser_supports_export_and_quotes(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        "\n".join(
            [
                "export AI_TRADING_SIGNAL_GATEWAY_ENABLED=true",
                'AI_TRADING_SIGNAL_GATEWAY_URL="https://orders.hyperalpha.org/api/ai-trading/signals"',
                "AI_TRADING_SIGNAL_GATEWAY_TOKEN='secret-token-value'",
                "AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true",
            ]
        ),
        encoding="utf-8",
    )

    env = production_check._parse_env_file(env_file)
    report = production_check.build_report(env)

    assert env["AI_TRADING_SIGNAL_GATEWAY_TOKEN"] == "secret-token-value"
    assert report["production_handoff_ready"] is True
    assert "secret-token-value" not in str(report)
