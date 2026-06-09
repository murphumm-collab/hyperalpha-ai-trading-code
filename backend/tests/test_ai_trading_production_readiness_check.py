import importlib.util
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "ai_trading_v1_production_readiness_check.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("ai_trading_v1_production_readiness_check", SCRIPT_PATH)
readiness_check = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = readiness_check
SPEC.loader.exec_module(readiness_check)


def _ready_env(**overrides):
    env = {
        "AUTH_REQUIRE_VERIFIED_BEARER": "true",
        "AUTH_JWKS_URL": "https://auth.hyperalpha.org/.well-known/jwks.json",
        "AUTH_JWT_ISSUER": "https://auth.hyperalpha.org",
        "AUTH_JWT_AUDIENCE": "hyperalpha-app",
        "AUTH_JWT_ALGORITHMS": "RS256",
        "AUTH_ADMIN_USERNAMES": "ops-admin",
        "AI_TRADING_SIGNAL_GATEWAY_ENABLED": "true",
        "AI_TRADING_SIGNAL_GATEWAY_URL": "https://orders.hyperalpha.org/api/ai-trading/signals",
        "AI_TRADING_SIGNAL_GATEWAY_TOKEN": "secret-order-gateway-token",
        "AI_TRADING_SIGNAL_GATEWAY_TIMEOUT_SECONDS": "10",
        "AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS": "300",
        "AI_TRADING_PRODUCTION_HANDOFF_APPROVED": "true",
        "AI_STREAM_MAX_RUNNING_GLOBAL": "12",
        "AI_STREAM_MAX_RUNNING_PER_USER": "2",
        "AI_TASK_MAX_WORKERS": "12",
        "AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED": "true",
        "AI_STREAM_DISTRIBUTED_WORKER_ENABLED": "true",
        "AI_STREAM_REDIS_URL": "redis://redis:6379/0",
        "AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN": "false",
        "AI_HARD_MAX_ORDER_NOTIONAL_USD": "1000",
        "AI_HARD_MAX_LEVERAGE": "10",
        "AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION": "0.25",
        "AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT": "50",
        "AI_HARD_REQUIRE_STOP_LOSS": "true",
        "AI_HARD_REQUIRE_TAKE_PROFIT": "true",
    }
    env.update(overrides)
    return env


def test_default_env_is_not_production_ready_and_reports_components():
    report = readiness_check.build_report({})

    assert report["production_ready"] is False
    assert "auth:auth_verified_bearer_required" in report["blockers"]
    assert "signal_handoff:signal_gateway_disabled" in report["blockers"]
    assert "hard_risk:ai_hard_max_order_notional_required" in report["blockers"]
    assert report["checks"]["model_policy"]["ready"] is True


def test_ready_env_passes_without_returning_secret_values():
    report = readiness_check.build_report(
        _ready_env(
            DEEPSEEK_API_KEY="secret-deepseek-key",
        )
    )

    assert report["production_ready"] is True
    assert report["blockers"] == []
    assert report["checks"]["signal_handoff"]["checks"]["token_present"] is True
    assert report["checks"]["signal_handoff"]["checks"]["token_value_returned"] is False
    assert report["checks"]["model_policy"]["checks"]["platform_model_key_envs_present"] == ["DEEPSEEK_API_KEY"]
    assert "model_policy:platform_model_key_env_present_user_profile_keys_preferred" in report["warnings"]
    serialized = str(report)
    assert "secret-order-gateway-token" not in serialized
    assert "secret-deepseek-key" not in serialized


def test_auth_and_distributed_ai_stream_blockers_are_specific():
    report = readiness_check.build_report(
        _ready_env(
            AUTH_JWKS_URL="http://127.0.0.1/jwks.json",
            AUTH_JWT_ALGORITHMS="HS256",
            AUTH_ADMIN_USERNAMES="default,ops-admin",
            AI_STREAM_REDIS_URL="",
            AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN="true",
        )
    )

    assert report["production_ready"] is False
    assert "auth:auth_jwks_url_must_be_https" in report["blockers"]
    assert "auth:auth_jwks_url_must_not_be_local_or_private" in report["blockers"]
    assert "auth:auth_jwt_algorithms_must_be_rs" in report["blockers"]
    assert "auth:auth_default_admin_user_must_be_removed" in report["blockers"]
    assert "ai_stream:ai_stream_redis_url_required_for_distributed_mode" in report["blockers"]
    assert "ai_stream:ai_stream_distributed_fail_open_must_be_false" in report["blockers"]


def test_env_file_parser_is_reused_without_leaking_tokens(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        "\n".join(
            [
                "export AUTH_REQUIRE_VERIFIED_BEARER=true",
                "AUTH_JWKS_URL=https://auth.hyperalpha.org/.well-known/jwks.json",
                "AUTH_JWT_ISSUER=https://auth.hyperalpha.org",
                "AUTH_JWT_AUDIENCE=hyperalpha-app",
                "AUTH_JWT_ALGORITHMS=RS256",
                "AUTH_ADMIN_USERNAMES=ops-admin",
                "AI_TRADING_SIGNAL_GATEWAY_ENABLED=true",
                "AI_TRADING_SIGNAL_GATEWAY_URL=https://orders.hyperalpha.org/api/ai-trading/signals",
                "AI_TRADING_SIGNAL_GATEWAY_TOKEN='secret-order-gateway-token'",
                "AI_TRADING_PRODUCTION_HANDOFF_APPROVED=true",
                "AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS=300",
                "AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED=true",
                "AI_STREAM_DISTRIBUTED_WORKER_ENABLED=true",
                "AI_STREAM_REDIS_URL=redis://redis:6379/0",
                "AI_HARD_MAX_ORDER_NOTIONAL_USD=1000",
                "AI_HARD_MAX_LEVERAGE=10",
                "AI_HARD_REQUIRE_STOP_LOSS=true",
                "AI_HARD_REQUIRE_TAKE_PROFIT=true",
            ]
        ),
        encoding="utf-8",
    )

    env = readiness_check._load_env(str(env_file))
    report = readiness_check.build_report(env)

    assert env["AI_TRADING_SIGNAL_GATEWAY_TOKEN"] == "secret-order-gateway-token"
    assert report["production_ready"] is True
    assert "secret-order-gateway-token" not in str(report)
