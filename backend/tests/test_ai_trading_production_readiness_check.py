import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import (
    AiTradingAgentSessionRecord,
    AiTradingSignalEventRecord,
    AiTradingSignalHandoffAttemptRecord,
    AiTradingStrategySpecRecord,
    User,
)


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


def test_non_http_signal_gateway_mode_blocks_aggregate_readiness_without_secret_leakage():
    report = readiness_check.build_report(
        _ready_env(
            AI_TRADING_SIGNAL_GATEWAY_MODE="rabbitmq",
        )
    )

    assert report["production_ready"] is False
    assert "signal_handoff:signal_gateway_mode_must_be_http_json" in report["blockers"]
    assert report["checks"]["signal_handoff"]["checks"]["gateway_mode"] == "rabbitmq"
    assert report["checks"]["signal_handoff"]["checks"]["supported_gateway_modes"] == ["http"]
    assert "secret-order-gateway-token" not in str(report)


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


def test_include_db_audits_adds_handoff_and_agent_context_gates_without_secret_leakage(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'readiness_with_db_audits.db'}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        user = User(username="ops-admin", role="admin", is_active="true")
        session.add(user)
        session.flush()
        spec = AiTradingStrategySpecRecord(
            user_id=user.id,
            name="CLI DB audit spec",
            symbol="BTC",
            status="approved",
            source="pytest",
            spec_json=json.dumps({"symbol": "BTC"}),
            validation_json=json.dumps({"status": "ok"}),
        )
        session.add(spec)
        session.flush()
        event = AiTradingSignalEventRecord(
            user_id=user.id,
            strategy_spec_id=spec.id,
            symbol="BTC",
            action="buy",
            status="review_candidate",
            handoff_status="failed",
            signal_json=json.dumps({"symbol": "BTC"}),
        )
        session.add(event)
        session.flush()
        session.add_all([
            AiTradingSignalHandoffAttemptRecord(
                user_id=user.id,
                signal_event_id=event.id,
                strategy_spec_id=spec.id,
                symbol="BTC",
                action="buy",
                result="failed",
                gateway_ready=True,
                blockers_json=json.dumps([]),
                eligibility_json=json.dumps({"authorization": "secret-db-audit-auth"}),
                error_message="failed with secret-db-audit-token",
                created_at=datetime(2026, 6, 9, 12, 0, 0),
            ),
            AiTradingAgentSessionRecord(
                user_id=user.id,
                agent_session_id="session:over-budget-cli",
                name="Over Budget CLI",
                context_summary="x" * 2001,
                status="active",
            ),
        ])
        session.commit()
    finally:
        session.close()

    report = readiness_check.build_readiness_report(
        _ready_env(),
        include_db_audits=True,
        session_factory=Session,
    )

    assert report["production_ready"] is False
    assert "agent_session_context:agent_session_context_over_budget_present" in report["blockers"]
    assert "handoff_audit:handoff_attempt_failed_present" in report["warnings"]
    assert report["checks"]["handoff_audit"]["checks"]["by_result"] == {"failed": 1}
    assert report["checks"]["agent_session_context"]["checks"]["over_budget_count"] == 1
    assert report["checks"]["handoff_audit"]["checks"]["secret_values_returned"] is False
    assert report["checks"]["agent_session_context"]["checks"]["secret_values_returned"] is False
    locator_action = next(
        action for action in report["next_actions"]
        if "Latest over-budget AI Trading agent context locator" in action
    )
    assert "session=session:over-budget-cli" in locator_action
    assert "status=active" in locator_action
    assert "chars=2001" in locator_action
    serialized = str(report)
    assert "secret-db-audit-auth" not in serialized
    assert "secret-db-audit-token" not in serialized
    assert "xxxxxxxx" not in serialized


def test_include_db_audits_fails_closed_without_leaking_database_error_text():
    secret_fixture = "secret-db-" + "password"

    def broken_session_factory():
        raise RuntimeError(f"database password={secret_fixture}")

    report = readiness_check.build_readiness_report(
        _ready_env(),
        include_db_audits=True,
        session_factory=broken_session_factory,
    )

    assert report["production_ready"] is False
    assert "db_audit:db_audit_unavailable" in report["blockers"]
    assert report["checks"]["db_audit"]["ready"] is False
    assert report["checks"]["db_audit"]["checks"] == {
        "error_type": "RuntimeError",
        "secret_values_returned": False,
    }
    serialized = str(report)
    assert secret_fixture not in serialized
    assert "password=" not in serialized
