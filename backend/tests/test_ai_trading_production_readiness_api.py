from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.ai_trading_routes import router
from database.connection import Base, get_db
from database.models import (
    AiTradingSignalEventRecord,
    AiTradingSignalHandoffAttemptRecord,
    AiTradingStrategySpecRecord,
    User,
    UserAuthSession,
)


RELEVANT_ENV_NAMES = {
    "AUTH_REQUIRE_VERIFIED_BEARER",
    "AUTH_JWKS_URL",
    "AUTH_JWT_ISSUER",
    "AUTH_JWT_AUDIENCE",
    "AUTH_JWT_ALGORITHMS",
    "AUTH_ADMIN_USERNAMES",
    "AI_TRADING_SIGNAL_GATEWAY_ENABLED",
    "AI_TRADING_SIGNAL_GATEWAY_URL",
    "AI_TRADING_SIGNAL_GATEWAY_TOKEN",
    "AI_TRADING_SIGNAL_GATEWAY_TIMEOUT_SECONDS",
    "AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS",
    "AI_TRADING_PRODUCTION_HANDOFF_APPROVED",
    "AI_STREAM_MAX_RUNNING_GLOBAL",
    "AI_STREAM_MAX_RUNNING_PER_USER",
    "AI_TASK_MAX_WORKERS",
    "AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED",
    "AI_STREAM_DISTRIBUTED_WORKER_ENABLED",
    "AI_STREAM_REDIS_URL",
    "AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN",
    "AI_HARD_MAX_ORDER_NOTIONAL_USD",
    "AI_HARD_MAX_LEVERAGE",
    "AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION",
    "AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT",
    "AI_HARD_REQUIRE_STOP_LOSS",
    "AI_HARD_REQUIRE_TAKE_PROFIT",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "QWEN_API_KEY",
    "DASHSCOPE_API_KEY",
}


def _build_client(tmp_path):
    db_path = tmp_path / "ai_trading_readiness_api.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    admin = User(username="ops-admin", role="admin", is_active="true")
    ordinary = User(username="ordinary-user", role="user", is_active="true")
    session.add_all([admin, ordinary])
    session.flush()
    admin_token = "admin-readiness-token"
    ordinary_token = "ordinary-readiness-token"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    session.add_all([
        UserAuthSession(user_id=admin.id, session_token=admin_token, expires_at=expires_at),
        UserAuthSession(user_id=ordinary.id, session_token=ordinary_token, expires_at=expires_at),
    ])
    session.commit()
    admin_id = admin.id
    session.close()

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    client._ai_trading_session_factory = Session
    return client, admin_token, ordinary_token, admin_id


def _clear_relevant_env(monkeypatch):
    for name in RELEVANT_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _set_ready_env(monkeypatch):
    _clear_relevant_env(monkeypatch)
    values = {
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
        "DEEPSEEK_API_KEY": "secret-deepseek-key",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_admin_can_read_ai_trading_production_readiness_without_secret_leakage(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, admin_id = _build_client(tmp_path)

    response = client.get(f"/api/ai-trading/admin/production-readiness?session_token={admin_token}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["requested_by_user_id"] == admin_id
    assert data["readiness"]["production_ready"] is True
    assert data["readiness"]["blockers"] == []
    assert data["readiness"]["checks"]["signal_handoff"]["checks"]["token_present"] is True
    assert data["readiness"]["checks"]["signal_handoff"]["checks"]["token_value_returned"] is False
    assert data["readiness"]["checks"]["model_policy"]["checks"]["platform_model_key_envs_present"] == [
        "DEEPSEEK_API_KEY"
    ]
    serialized = str(data)
    assert "secret-order-gateway-token" not in serialized
    assert "secret-deepseek-key" not in serialized


def test_admin_readiness_reports_handoff_attempt_audit_warnings_without_attempt_secrets(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, admin_id = _build_client(tmp_path)
    session = client._ai_trading_session_factory()
    try:
        spec = AiTradingStrategySpecRecord(
            user_id=admin_id,
            name="Admin readiness audit spec",
            symbol="BTC",
            status="approved",
            source="pytest",
            spec_json=json.dumps({"symbol": "BTC"}),
            validation_json=json.dumps({"status": "ok"}),
        )
        session.add(spec)
        session.flush()
        event = AiTradingSignalEventRecord(
            user_id=admin_id,
            strategy_spec_id=spec.id,
            symbol="BTC",
            action="buy",
            status="review_candidate",
            handoff_status="failed",
            signal_json=json.dumps({"symbol": "BTC"}),
        )
        session.add(event)
        session.flush()
        failed_attempt = AiTradingSignalHandoffAttemptRecord(
            user_id=admin_id,
            signal_event_id=event.id,
            strategy_spec_id=spec.id,
            symbol="BTC",
            action="buy",
            result="failed",
            gateway_ready=True,
            blockers_json=json.dumps([]),
            eligibility_json=json.dumps({
                "gateway_response": {
                    "authorization": "secret-attempt-authorization",
                    "body": "secret-attempt-body",
                },
            }),
            error_message="Signal gateway handoff failed with secret-attempt-token",
            created_at=datetime(2026, 6, 9, 12, 0, 0),
        )
        blocked_attempt = AiTradingSignalHandoffAttemptRecord(
            user_id=admin_id,
            signal_event_id=event.id,
            strategy_spec_id=spec.id,
            symbol="BTC",
            action="buy",
            result="blocked",
            gateway_ready=False,
            blockers_json=json.dumps(["gateway_disabled"]),
            eligibility_json=json.dumps({"api_key": "secret-attempt-key"}),
            error_message="gateway_disabled",
            created_at=datetime(2026, 6, 9, 12, 1, 0),
        )
        session.add_all([failed_attempt, blocked_attempt])
        session.flush()
        spec_id = spec.id
        event_id = event.id
        blocked_attempt_id = blocked_attempt.id
        session.commit()
    finally:
        session.close()

    response = client.get(f"/api/ai-trading/admin/production-readiness?session_token={admin_token}")

    assert response.status_code == 200
    readiness = response.json()["readiness"]
    assert readiness["production_ready"] is True
    assert readiness["blockers"] == []
    assert "handoff_audit:handoff_attempt_failed_present" in readiness["warnings"]
    assert "handoff_audit:handoff_attempt_blocked_present" in readiness["warnings"]
    handoff_audit = readiness["checks"]["handoff_audit"]
    assert handoff_audit["ready"] is True
    assert handoff_audit["checks"]["total"] == 2
    assert handoff_audit["checks"]["by_result"] == {"blocked": 1, "failed": 1}
    assert handoff_audit["checks"]["gateway_ready"] == 1
    assert handoff_audit["checks"]["gateway_not_ready"] == 1
    assert handoff_audit["checks"]["latest_non_submitted"] == {
        "id": blocked_attempt_id,
        "signal_event_id": event_id,
        "strategy_spec_id": spec_id,
        "symbol": "BTC",
        "action": "buy",
        "result": "blocked",
        "gateway_ready": False,
    }
    assert handoff_audit["checks"]["secret_values_returned"] is False
    next_actions = readiness["next_actions"]
    assert any("failed AI Trading signal handoff attempts" in action for action in next_actions)
    assert any("blocked AI Trading signal handoff attempts" in action for action in next_actions)
    serialized = str(response.json())
    assert "secret-attempt-authorization" not in serialized
    assert "secret-attempt-body" not in serialized
    assert "secret-attempt-key" not in serialized
    assert "secret-attempt-token" not in serialized


def test_ai_trading_production_readiness_api_requires_admin_session(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, _admin_token, ordinary_token, _admin_id = _build_client(tmp_path)

    anonymous = client.get("/api/ai-trading/admin/production-readiness")
    ordinary = client.get(f"/api/ai-trading/admin/production-readiness?session_token={ordinary_token}")

    assert anonymous.status_code == 401
    assert ordinary.status_code == 403


def test_admin_readiness_api_reports_default_blockers(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, admin_token, _ordinary_token, _admin_id = _build_client(tmp_path)

    response = client.get(f"/api/ai-trading/admin/production-readiness?session_token={admin_token}")

    assert response.status_code == 200
    readiness = response.json()["readiness"]
    assert readiness["production_ready"] is False
    assert "auth:auth_verified_bearer_required" in readiness["blockers"]
    assert "signal_handoff:signal_gateway_disabled" in readiness["blockers"]
    assert "hard_risk:ai_hard_max_order_notional_required" in readiness["blockers"]
