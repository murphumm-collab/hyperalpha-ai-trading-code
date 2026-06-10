from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.ai_trading_routes import router
from database.connection import Base, get_db
from database.models import (
    AiTradingAgentSessionRecord,
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


def _production_evidence_payload(*, include_secret: bool = False, missing_item: str | None = None):
    item_ids = [
        "macos_reboot_recovery",
        "real_model_profile_live_acceptance",
        "real_order_backend_handoff",
        "production_auth_hard_risk_readiness",
        "admin_readiness_real_auth_visual",
        "production_agent_session_visual",
        "real_exchange_execution",
    ]
    items = {}
    for item_id in item_ids:
        if item_id == missing_item:
            continue
        items[item_id] = {
            "status": "accepted",
            "validated_at": "2026-06-10T12:00:00Z",
            "validated_by": "ops-admin",
            "evidence_summary": f"{item_id} accepted with sanitized operational evidence.",
            "artifact_refs": [f"ops://ai-trading/{item_id}/acceptance"],
            "secret_values_returned": False,
        }
    if include_secret:
        items["real_order_backend_handoff"]["evidence_summary"] = (
            "accepted with Authorization: Bearer secret-production-token-123456789"
        )
    return {
        "version": "hyperalpha.ai_trading.external_acceptance.v1",
        "generated_at": "2026-06-10T12:05:00Z",
        "secret_values_returned": False,
        "items": items,
    }


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


def test_admin_can_read_ai_trading_production_evidence_explain_without_secret_leakage(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, admin_id = _build_client(tmp_path)

    response = client.get(f"/api/ai-trading/admin/production-evidence-explain?session_token={admin_token}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["requested_by_user_id"] == admin_id
    explain = data["explain"]
    assert explain["mode"] == "production_evidence_explain"
    assert explain["github_upload"] == "deferred_by_user_request"
    assert explain["local_v1_accepted"] is True
    assert explain["ready_for_live_orders"] is False
    assert explain["production_track"] == "pending_external_acceptance"
    assert explain["production_evidence"]["provided"] is False
    assert explain["production_evidence"]["ready"] is False
    assert explain["production_evidence"]["required_count"] == 7
    assert explain["schema"]["safe_artifact_ref_schemes"] == ["https", "lark", "notion", "ops"]
    assert explain["schema"]["required_item_fields"] == [
        "status=accepted",
        "validated_at=timezone-aware ISO-8601 timestamp",
        "validated_by=non-placeholder reviewer/operator name, 3-120 chars",
        "evidence_summary=concrete sanitized acceptance summary, 24-600 chars",
        "artifact_refs=1-5 safe refs using https://, ops://, lark://, or notion://",
        "secret_values_returned=false",
    ]
    assert explain["schema"]["required_item_ids"] == [
        "macos_reboot_recovery",
        "real_model_profile_live_acceptance",
        "real_order_backend_handoff",
        "production_auth_hard_risk_readiness",
        "admin_readiness_real_auth_visual",
        "production_agent_session_visual",
        "real_exchange_execution",
    ]
    items_by_id = {item["id"]: item for item in explain["items"]}
    assert set(items_by_id) == set(explain["schema"]["required_item_ids"])
    order_backend_item = items_by_id["real_order_backend_handoff"]
    assert order_backend_item["evidence_status"] == "not_provided"
    assert order_backend_item["ready"] is False
    assert order_backend_item["blockers"] == ["external_evidence_item_not_provided"]
    assert order_backend_item["safe_artifact_ref_schemes"] == ["https", "lark", "notion", "ops"]
    assert "API keys" in order_backend_item["forbidden_values"]
    assert "bearer tokens" in order_backend_item["forbidden_values"]
    assert any("real HTTPS order-backend" in action for action in order_backend_item["operator_guidance"])
    serialized = str(data)
    assert "secret-order-gateway-token" not in serialized
    assert "secret-deepseek-key" not in serialized


def test_admin_can_load_ai_trading_production_evidence_template_without_secret_leakage(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, admin_id = _build_client(tmp_path)

    response = client.get(f"/api/ai-trading/admin/production-evidence-template?session_token={admin_token}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["requested_by_user_id"] == admin_id
    assert data["ready_for_live_orders"] is False
    assert data["persistence"] == "not_stored"
    assert "path" not in data
    template = data["template"]
    assert template["version"] == "hyperalpha.ai_trading.external_acceptance.v1"
    assert template["generated_at"] is None
    assert template["secret_values_returned"] is False
    assert set(template["items"]) == {
        "macos_reboot_recovery",
        "real_model_profile_live_acceptance",
        "real_order_backend_handoff",
        "production_auth_hard_risk_readiness",
        "admin_readiness_real_auth_visual",
        "production_agent_session_visual",
        "real_exchange_execution",
    }
    assert all(item["status"] == "pending_external_acceptance" for item in template["items"].values())
    assert all(item["artifact_refs"] == [] for item in template["items"].values())
    serialized = str(data)
    assert "secret-order-gateway-token" not in serialized
    assert "secret-deepseek-key" not in serialized


def test_admin_can_validate_ai_trading_production_evidence_payload_without_live_unlock(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, admin_id = _build_client(tmp_path)

    response = client.post(
        f"/api/ai-trading/admin/production-evidence-validate?session_token={admin_token}",
        json={"evidence": _production_evidence_payload()},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["requested_by_user_id"] == admin_id
    validation = data["validation"]
    assert validation["mode"] == "production_evidence_payload_validation"
    assert validation["github_upload"] == "deferred_by_user_request"
    assert validation["local_v1_accepted"] is True
    assert validation["ready_for_live_orders"] is False
    assert validation["production_track"] == "external_evidence_accepted_pending_explicit_confirmation"
    assert validation["production_evidence"]["provided"] is True
    assert validation["production_evidence"]["path"] is None
    assert validation["production_evidence"]["ready"] is True
    assert validation["production_evidence"]["accepted_count"] == 7
    assert validation["production_evidence"]["required_count"] == 7
    assert validation["items"][0]["required_fields"]
    assert all(item["ready"] for item in validation["items"])
    serialized = str(data)
    assert "secret-order-gateway-token" not in serialized
    assert "secret-deepseek-key" not in serialized


def test_admin_evidence_payload_validation_reports_secret_blocker_without_echoing_secret(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, _admin_id = _build_client(tmp_path)

    response = client.post(
        f"/api/ai-trading/admin/production-evidence-validate?session_token={admin_token}",
        json={"evidence": _production_evidence_payload(include_secret=True)},
    )

    assert response.status_code == 200
    validation = response.json()["validation"]
    assert validation["ready_for_live_orders"] is False
    assert validation["production_evidence"]["ready"] is False
    assert "external_evidence_secret_pattern_detected" in validation["production_evidence"]["blockers"]
    order_item = next(item for item in validation["items"] if item["id"] == "real_order_backend_handoff")
    assert "external_evidence_secret_pattern_detected" in order_item["blockers"]
    serialized = str(response.json())
    assert "secret-production-token-123456789" not in serialized
    assert "Authorization: Bearer" not in serialized


def test_admin_evidence_payload_validation_rejects_oversized_payload_without_echoing_secret(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, _admin_id = _build_client(tmp_path)
    payload = _production_evidence_payload()
    payload["notes"] = [
        "oversized sanitized note " + ("x" * 41000) + " secret-production-token-123456789"
    ]

    response = client.post(
        f"/api/ai-trading/admin/production-evidence-validate?session_token={admin_token}",
        json={"evidence": payload},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "production_evidence_payload_too_large"
    serialized = str(response.json())
    assert "secret-production-token-123456789" not in serialized


def test_admin_evidence_payload_validation_rejects_too_many_item_keys(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, _admin_id = _build_client(tmp_path)
    payload = _production_evidence_payload()
    for index in range(20):
        payload["items"][f"unexpected_evidence_item_{index}"] = {
            "status": "accepted",
            "validated_at": "2026-06-10T12:00:00Z",
            "validated_by": "ops-admin",
            "evidence_summary": "unexpected item should be rejected before deep validation.",
            "artifact_refs": ["ops://ai-trading/unexpected/acceptance"],
            "secret_values_returned": False,
        }

    response = client.post(
        f"/api/ai-trading/admin/production-evidence-validate?session_token={admin_token}",
        json={"evidence": payload},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "production_evidence_items_too_many"


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


def test_admin_readiness_reports_agent_session_context_budget_without_summary_leakage(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, admin_id = _build_client(tmp_path)
    session = client._ai_trading_session_factory()
    try:
        session.add_all([
            AiTradingAgentSessionRecord(
                user_id=admin_id,
                agent_session_id="session:normal-context",
                name="Normal Context Session",
                context_summary="BTC breakout context with risk caps.",
                status="active",
            ),
            AiTradingAgentSessionRecord(
                user_id=admin_id,
                agent_session_id="session:redacted-context",
                name="Redacted Context Session",
                context_summary="[redacted_sensitive_context]",
                status="active",
            ),
            AiTradingAgentSessionRecord(
                user_id=admin_id,
                agent_session_id="session:sensitive-context",
                name="Sensitive Context Session",
                context_summary="api_key=secret-session-key should not be returned",
                status="active",
            ),
            AiTradingAgentSessionRecord(
                user_id=admin_id,
                agent_session_id="session:near-budget",
                name="Near Budget Session",
                context_summary="n" * 1800,
                status="archived",
            ),
            AiTradingAgentSessionRecord(
                user_id=admin_id,
                agent_session_id="session:over-budget",
                name="Over Budget Session",
                context_summary="o" * 2001,
                status="active",
            ),
        ])
        session.commit()
    finally:
        session.close()

    response = client.get(f"/api/ai-trading/admin/production-readiness?session_token={admin_token}")

    assert response.status_code == 200
    readiness = response.json()["readiness"]
    assert readiness["production_ready"] is False
    assert "agent_session_context:agent_session_context_over_budget_present" in readiness["blockers"]
    assert "agent_session_context:agent_session_context_near_budget_present" in readiness["warnings"]
    assert "agent_session_context:agent_session_context_redacted_present" in readiness["warnings"]
    assert "agent_session_context:agent_session_context_sensitive_present" in readiness["warnings"]
    agent_context = readiness["checks"]["agent_session_context"]
    assert agent_context["ready"] is False
    assert agent_context["checks"]["total"] == 5
    assert agent_context["checks"]["active"] == 4
    assert agent_context["checks"]["archived"] == 1
    assert agent_context["checks"]["with_context_summary"] == 5
    assert agent_context["checks"]["empty_context_summary"] == 0
    assert agent_context["checks"]["context_summary_max_chars"] == 2000
    assert agent_context["checks"]["near_budget_threshold_chars"] == 1800
    assert agent_context["checks"]["max_context_summary_chars"] == 2001
    assert agent_context["checks"]["near_budget_count"] == 1
    assert agent_context["checks"]["over_budget_count"] == 1
    assert agent_context["checks"]["redacted_context_summary_count"] == 1
    assert agent_context["checks"]["sensitive_context_summary_count"] == 1
    latest_over_budget = agent_context["checks"]["latest_over_budget"]
    assert isinstance(latest_over_budget["id"], int)
    assert {key: value for key, value in latest_over_budget.items() if key != "id"} == {
        "agent_session_id": "session:over-budget",
        "status": "active",
        "context_summary_chars": 2001,
    }
    latest_redacted_context = agent_context["checks"]["latest_redacted_context"]
    assert isinstance(latest_redacted_context["id"], int)
    assert {key: value for key, value in latest_redacted_context.items() if key != "id"} == {
        "agent_session_id": "session:redacted-context",
        "status": "active",
        "context_summary_chars": len("[redacted_sensitive_context]"),
    }
    latest_sensitive_context = agent_context["checks"]["latest_sensitive_context"]
    assert isinstance(latest_sensitive_context["id"], int)
    assert {key: value for key, value in latest_sensitive_context.items() if key != "id"} == {
        "agent_session_id": "session:sensitive-context",
        "status": "active",
        "context_summary_chars": len("api_key=secret-session-key should not be returned"),
    }
    assert agent_context["checks"]["secret_values_returned"] is False
    next_actions = readiness["next_actions"]
    assert any("over-budget AI Trading agent session summaries" in action for action in next_actions)
    assert any("near-budget AI Trading agent session summaries" in action for action in next_actions)
    assert any("redacted or sensitive-looking context" in action for action in next_actions)
    over_budget_locator_action = next(
        action for action in next_actions
        if "Latest over-budget AI Trading agent context locator" in action
    )
    assert "session=session:over-budget" in over_budget_locator_action
    assert "status=active" in over_budget_locator_action
    assert "chars=2001" in over_budget_locator_action
    redacted_locator_action = next(
        action for action in next_actions
        if "Latest redacted AI Trading agent context locator" in action
    )
    assert "session=session:redacted-context" in redacted_locator_action
    assert f"chars={len('[redacted_sensitive_context]')}" in redacted_locator_action
    sensitive_locator_action = next(
        action for action in next_actions
        if "Latest sensitive-looking AI Trading agent context locator" in action
    )
    assert "session=session:sensitive-context" in sensitive_locator_action
    assert "secret-session-key" not in sensitive_locator_action
    serialized = str(response.json())
    assert "secret-session-key" not in serialized
    assert "BTC breakout context with risk caps" not in serialized
    assert "nnnnnnnn" not in serialized
    assert "oooooooo" not in serialized


def test_ai_trading_production_readiness_api_requires_admin_session(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, _admin_token, ordinary_token, _admin_id = _build_client(tmp_path)

    anonymous = client.get("/api/ai-trading/admin/production-readiness")
    ordinary = client.get(f"/api/ai-trading/admin/production-readiness?session_token={ordinary_token}")

    assert anonymous.status_code == 401
    assert ordinary.status_code == 403


def test_ai_trading_production_evidence_explain_api_requires_admin_session(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, _admin_token, ordinary_token, _admin_id = _build_client(tmp_path)

    anonymous = client.get("/api/ai-trading/admin/production-evidence-explain")
    ordinary = client.get(f"/api/ai-trading/admin/production-evidence-explain?session_token={ordinary_token}")

    assert anonymous.status_code == 401
    assert ordinary.status_code == 403


def test_ai_trading_production_evidence_template_api_requires_admin_session(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, _admin_token, ordinary_token, _admin_id = _build_client(tmp_path)

    anonymous = client.get("/api/ai-trading/admin/production-evidence-template")
    ordinary = client.get(f"/api/ai-trading/admin/production-evidence-template?session_token={ordinary_token}")

    assert anonymous.status_code == 401
    assert ordinary.status_code == 403


def test_ai_trading_production_evidence_validate_api_requires_admin_session(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, _admin_token, ordinary_token, _admin_id = _build_client(tmp_path)
    payload = {"evidence": _production_evidence_payload()}

    anonymous = client.post("/api/ai-trading/admin/production-evidence-validate", json=payload)
    ordinary = client.post(
        f"/api/ai-trading/admin/production-evidence-validate?session_token={ordinary_token}",
        json=payload,
    )

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
