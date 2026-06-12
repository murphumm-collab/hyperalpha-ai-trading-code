from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.ai_stream_routes import router as ai_stream_router
from api.ai_trading_routes import router as ai_trading_router
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


def _utc_iso(offset: timedelta = timedelta()) -> str:
    value = datetime.now(timezone.utc) + offset
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    app.include_router(ai_trading_router)
    app.include_router(ai_stream_router)
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
    evidence_run_id = "ops-20260610-cutover-001"
    summaries = {
        "macos_reboot_recovery": (
            "macOS reboot accepted with LaunchAgent restored, runtime mirror current, and ready=true readiness."
        ),
        "real_model_profile_live_acceptance": (
            "DeepSeek live model-adjust accepted with no signal event, no handoff, and no orders."
        ),
        "real_order_backend_handoff": (
            "HTTPS order backend accepted with mode=http, token-present, and production_handoff_approved=true."
        ),
        "production_auth_hard_risk_readiness": (
            "JWKS and hard risk accepted with stop loss, take profit, and secret_values_returned=false."
        ),
        "admin_readiness_real_auth_visual": (
            "Admin real auth accepted with production readiness panel visible and no secrets or token rendered."
        ),
        "production_agent_session_visual": (
            "Agent-session current user visual accepted with context budget and no context_summary rendered."
        ),
        "real_exchange_execution": (
            "Order backend Hyperliquid exchange execution accepted as not AI agent with sanitized execution evidence."
        ),
    }
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
            "validated_at": _utc_iso(timedelta(minutes=-5)),
            "validated_by": "ops-admin",
            "evidence_summary": summaries[item_id],
            "artifact_refs": [f"ops://ai-trading/{evidence_run_id}/{item_id}/acceptance"],
            "secret_values_returned": False,
        }
    if include_secret:
        items["real_order_backend_handoff"]["evidence_summary"] = (
            "accepted with Authorization: Bearer secret-production-token-123456789"
        )
    return {
        "version": "hyperalpha.ai_trading.external_acceptance.v1",
        "evidence_run_id": evidence_run_id,
        "generated_at": _utc_iso(timedelta(minutes=-2)),
        "expires_at": _utc_iso(timedelta(days=1)),
        "cutover_window": {
            "start_at": _utc_iso(timedelta(minutes=-10)),
            "end_at": _utc_iso(timedelta(hours=2)),
        },
        "cutover_approval_ref": f"ops://ai-trading/{evidence_run_id}/production-cutover/approval",
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
    assert explain["production_evidence"]["evidence_run_id_present"] is False
    assert explain["production_evidence"]["expires_at"] is None
    assert explain["production_evidence"]["cutover_window_present"] is False
    assert explain["production_evidence"]["cutover_window_start_at"] is None
    assert explain["production_evidence"]["cutover_window_end_at"] is None
    assert explain["production_evidence"]["cutover_approval_ref_present"] is False
    assert explain["progress"]["status"] == "pending_external_acceptance"
    assert explain["progress"]["accepted_item_ids"] == []
    assert explain["progress"]["pending_item_ids"] == explain["schema"]["required_item_ids"]
    assert explain["progress"]["blocked_item_ids"] == explain["schema"]["required_item_ids"]
    assert explain["progress"]["next_required_item_ids"] == explain["schema"]["required_item_ids"]
    assert explain["progress"]["accepted_count"] == 0
    assert explain["progress"]["pending_count"] == 7
    assert explain["progress"]["blocked_count"] == 7
    assert explain["progress"]["required_count"] == 7
    assert explain["progress"]["live_order_gate_blockers"] == ["production_evidence_not_ready"]
    assert len(explain["progress"]["next_required_actions"]) == 7
    assert len(explain["progress"]["root_next_required_actions"]) >= 6
    assert explain["progress"]["next_required_actions"][0].startswith(
        "macos_reboot_recovery: After a real macOS reboot"
    )
    assert any(
        action.startswith("root.evidence_run_id:")
        for action in explain["progress"]["root_next_required_actions"]
    )
    assert any(
        action.startswith("root.cutover_window:")
        for action in explain["progress"]["root_next_required_actions"]
    )
    assert any(
        action.startswith("real_order_backend_handoff: Configure the real HTTPS order-backend")
        for action in explain["progress"]["next_required_actions"]
    )
    assert explain["schema"]["safe_artifact_ref_schemes"] == ["https", "lark", "notion", "ops"]
    assert explain["schema"]["max_evidence_validity_days"] == 7
    assert explain["schema"]["max_clock_skew_seconds"] == 300
    assert explain["schema"]["max_item_validation_age_days"] == 7
    assert explain["schema"]["max_cutover_window_hours"] == 8
    assert explain["schema"]["min_evidence_run_id_chars"] == 12
    assert explain["schema"]["max_evidence_run_id_chars"] == 80
    assert (
        "evidence_run_id=safe unique run id, 12-80 chars, letters/numbers/._:- only, referenced by cutover_approval_ref and item artifact_refs"
        in explain["schema"]["required_root_fields"]
    )
    assert (
        "generated_at=timezone-aware ISO-8601 timestamp not more than 300 seconds in the future"
        in explain["schema"]["required_root_fields"]
    )
    assert (
        "expires_at=timezone-aware ISO-8601 timestamp after generated_at, in the future, and within 7 days"
        in explain["schema"]["required_root_fields"]
    )
    assert (
        "cutover_window=start_at/end_at timezone-aware ISO-8601 window containing the production audit time and no longer than 8 hours"
        in explain["schema"]["required_root_fields"]
    )
    assert explain["schema"]["required_item_fields"] == [
        "status=accepted",
        "validated_at=timezone-aware ISO-8601 timestamp not more than 300 seconds in the future and not older than 7 days at generated_at",
        "validated_by=non-placeholder reviewer/operator name, 3-120 chars",
        "evidence_summary=concrete sanitized acceptance summary, 24-600 chars",
        "artifact_refs=1-5 unique item-specific safe refs using https://, ops://, lark://, or notion:// and containing evidence_run_id plus the item id",
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
    assert data["guidance"]["secret_policy"] == "metadata_only_no_env_or_credentials"
    assert len(data["guidance"]["root_fields"]) >= 6
    run_id_guidance = next(
        field for field in data["guidance"]["root_fields"] if field["field"] == "evidence_run_id"
    )
    assert "external_evidence_run_id_missing" in run_id_guidance["related_blockers"]
    assert any("cutover_approval_ref" in hint for hint in run_id_guidance["operator_guidance"])
    assert len(data["guidance"]["root_next_required_actions"]) >= 6
    assert any(
        action.startswith("root.evidence_run_id:") and "cutover_approval_ref" in action
        for action in data["guidance"]["root_next_required_actions"]
    )
    assert any(
        action.startswith("root.cutover_window:") and "approved live-order cutover window" in action
        for action in data["guidance"]["root_next_required_actions"]
    )
    assert len(data["guidance"]["items"]) == 7
    assert len(data["guidance"]["next_required_actions"]) == 7
    assert any(
        action.startswith("real_order_backend_handoff: Configure the real HTTPS order-backend")
        for action in data["guidance"]["next_required_actions"]
    )
    order_guidance = next(
        item for item in data["guidance"]["items"] if item["id"] == "real_order_backend_handoff"
    )
    assert "mode=http / gateway mode=http / gateway_mode=http" in order_guidance["required_summary_terms"]
    assert "bearer tokens" in order_guidance["forbidden_values"]
    template = data["template"]
    assert template["version"] == "hyperalpha.ai_trading.external_acceptance.v1"
    assert template["evidence_run_id"] is None
    assert template["generated_at"] is None
    assert template["expires_at"] is None
    assert template["cutover_window"] == {"start_at": None, "end_at": None}
    assert template["cutover_approval_ref"] is None
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
    assert data["dry_run"] == {
        "mode": "admin_payload_validation_only",
        "accepted_input": "json_value_for_safe_validation",
        "expected_input": "json_object",
        "root_is_object": True,
        "persistence": "not_stored",
        "payload_bytes": data["dry_run"]["payload_bytes"],
        "max_payload_bytes": 40000,
        "item_key_count": 7,
        "max_item_keys": 14,
        "network_calls": False,
        "model_calls": False,
        "order_backend_calls": False,
        "exchange_calls": False,
        "github_calls": False,
        "ready_for_live_orders": False,
        "live_orders_unlocked": False,
        "secret_policy": "metadata_only_no_env_or_credentials",
    }
    assert data["dry_run"]["payload_bytes"] > 0
    assert "evidence" not in data["dry_run"]
    assert "path" not in data["dry_run"]
    assert data["guidance"]["secret_policy"] == "metadata_only_no_env_or_credentials"
    assert any(
        field["field"] == "cutover_window"
        and "external_evidence_cutover_window_start_at_missing" in field["related_blockers"]
        for field in data["guidance"]["root_fields"]
    )
    assert any(
        action.startswith("root.cutover_approval_ref:")
        for action in data["guidance"]["root_next_required_actions"]
    )
    assert len(data["guidance"]["next_required_actions"]) == 7
    assert any(
        action.startswith("real_order_backend_handoff: Configure the real HTTPS order-backend")
        for action in data["guidance"]["next_required_actions"]
    )
    validation = data["validation"]
    assert validation["mode"] == "production_evidence_payload_validation"
    assert validation["github_upload"] == "deferred_by_user_request"
    assert validation["local_v1_accepted"] is True
    assert validation["ready_for_live_orders"] is False
    assert validation["production_track"] == "external_evidence_accepted_pending_explicit_confirmation"
    assert validation["production_evidence"]["provided"] is True
    assert validation["production_evidence"]["path"] is None
    assert validation["production_evidence"]["ready"] is True
    assert validation["production_evidence"]["evidence_run_id_present"] is True
    assert validation["production_evidence"]["accepted_count"] == 7
    assert validation["production_evidence"]["required_count"] == 7
    assert validation["production_evidence"]["cutover_approval_ref_present"] is True
    assert validation["progress"]["status"] == "external_evidence_accepted_pending_explicit_confirmation"
    assert validation["progress"]["accepted_item_ids"] == validation["schema"]["required_item_ids"]
    assert validation["progress"]["pending_item_ids"] == []
    assert validation["progress"]["blocked_item_ids"] == []
    assert validation["progress"]["next_required_item_ids"] == []
    assert validation["progress"]["accepted_count"] == 7
    assert validation["progress"]["pending_count"] == 0
    assert validation["progress"]["blocked_count"] == 0
    assert validation["progress"]["required_count"] == 7
    assert validation["progress"]["next_required_actions"] == []
    assert validation["progress"]["root_next_required_actions"] == []
    assert validation["progress"]["live_order_gate_blockers"] == [
        "explicit_live_ready_confirmation_required"
    ]
    assert validation["items"][0]["required_fields"]
    assert all(item["ready"] for item in validation["items"])
    serialized = str(data)
    assert "secret-order-gateway-token" not in serialized
    assert "secret-deepseek-key" not in serialized


def test_admin_evidence_payload_validation_handles_non_object_without_echoing_secret(tmp_path, monkeypatch):
    _set_ready_env(monkeypatch)
    client, admin_token, _ordinary_token, _admin_id = _build_client(tmp_path)

    response = client.post(
        f"/api/ai-trading/admin/production-evidence-validate?session_token={admin_token}",
        json={"evidence": "Authorization: Bearer secret-production-token-123456789"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dry_run"]["mode"] == "admin_payload_validation_only"
    assert data["dry_run"]["accepted_input"] == "json_value_for_safe_validation"
    assert data["dry_run"]["expected_input"] == "json_object"
    assert data["dry_run"]["root_is_object"] is False
    assert data["dry_run"]["item_key_count"] == 0
    assert data["dry_run"]["live_orders_unlocked"] is False
    validation = data["validation"]
    assert validation["ready_for_live_orders"] is False
    assert validation["production_evidence"]["ready"] is False
    assert validation["production_evidence"]["secret_pattern_count"] >= 1
    assert "external_evidence_root_must_be_object" in validation["production_evidence"]["blockers"]
    assert "external_evidence_secret_pattern_detected" in validation["production_evidence"]["blockers"]
    assert validation["progress"]["root_next_required_actions"][0].startswith("root.schema:")
    serialized = str(data)
    assert "secret-production-token-123456789" not in serialized
    assert "Authorization: Bearer" not in serialized


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
            "validated_at": _utc_iso(timedelta(minutes=-5)),
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


def test_admin_ai_runtime_sanitizes_component_last_errors(tmp_path, monkeypatch):
    _clear_relevant_env(monkeypatch)
    client, admin_token, ordinary_token, admin_id = _build_client(tmp_path)
    redis_error = "redis://:secret-redis-password@redis.internal:6379/0 Authorization: Bearer leaked"
    dispatch_error = "OperationalError gateway token=secret-dispatch-token"

    def fake_runtime_stats():
        return {
            "runner_id": "pytest-runner",
            "running_tasks": 0,
            "remote_running_tasks": 0,
            "effective_running_tasks": 0,
            "persisted_running_tasks": 0,
            "stale_running_tasks": 0,
            "completed_buffered_tasks": 0,
            "error_buffered_tasks": 0,
            "total_buffered_tasks": 0,
            "task_max_workers": 12,
            "task_max_running_global": 12,
            "task_max_running_per_user": 2,
            "task_threads": 0,
            "task_queue": 0,
            "background_max_workers": 4,
            "background_threads": 0,
            "background_queue": 0,
            "distributed_admission": {
                "enabled": True,
                "available": False,
                "lease_ttl_seconds": 30,
                "last_error": redis_error,
            },
            "dispatch_queue": {
                "enabled": True,
                "claim_stale_seconds": 60,
                "pending": 0,
                "claimed": 0,
                "running": 0,
                "completed": 0,
                "failed": 1,
                "total": 1,
                "last_error": dispatch_error,
            },
            "users": [
                {
                    "user_id": admin_id,
                    "total_tasks": 0,
                    "running_tasks": 0,
                    "remote_running_tasks": 0,
                    "persisted_running_tasks": 0,
                    "stale_running_tasks": 0,
                    "completed_tasks": 0,
                    "error_tasks": 0,
                }
            ],
        }

    monkeypatch.setattr("api.ai_stream_routes.get_ai_runtime_stats", fake_runtime_stats)

    ordinary = client.get(f"/api/ai-stream/admin/runtime?session_token={ordinary_token}")
    assert ordinary.status_code == 403

    response = client.get(f"/api/ai-stream/admin/runtime?session_token={admin_token}")
    assert response.status_code == 200
    data = response.json()

    distributed = data["distributed_admission"]
    assert distributed["last_error_present"] is True
    assert distributed["last_error_code"] == "distributed_admission_unavailable"
    assert distributed["last_error"] == "distributed_admission_unavailable"

    dispatch = data["dispatch_queue"]
    assert dispatch["last_error_present"] is True
    assert dispatch["last_error_code"] == "dispatch_queue_stats_unavailable"
    assert dispatch["last_error"] == "dispatch_queue_stats_unavailable"

    serialized = json.dumps(data, ensure_ascii=False)
    assert redis_error not in serialized
    assert dispatch_error not in serialized
    assert "secret-redis-password" not in serialized
    assert "Bearer leaked" not in serialized
    assert "secret-dispatch-token" not in serialized


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
