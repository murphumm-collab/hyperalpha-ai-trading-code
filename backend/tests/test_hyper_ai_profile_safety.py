import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth_utils import get_current_user_dependency
from api.hyper_ai_routes import router
from database.connection import Base, get_db
from database.models import HyperAiProfile, User
from services import hyper_ai_service


def _build_client(tmp_path):
    db_path = tmp_path / "hyper_ai_profile_safety.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    user = User(username="profile-safety-user", is_active="true")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user_dependency] = lambda: SimpleNamespace(id=user_id)
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    client._hyper_ai_session_factory = Session
    client._hyper_ai_user_id = user_id
    return client


def _assert_no_secret_echo(text: str) -> None:
    rendered = text.lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "postgres://" not in rendered
    assert "private_key" not in rendered
    assert "secret-profile" not in rendered
    assert "secret-token" not in rendered


def test_profile_preferences_reject_sensitive_content_without_echo(tmp_path) -> None:
    client = _build_client(tmp_path)

    response = client.post(
        "/api/hyper-ai/profile/preferences",
        json={
            "trading_style": "api_key=secret-profile-key trend following",
            "risk_preference": "moderate",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": hyper_ai_service.SENSITIVE_PROFILE_FIELD_ERROR}
    _assert_no_secret_echo(response.text)

    with client._hyper_ai_session_factory() as db:
        profile = db.query(HyperAiProfile).filter(
            HyperAiProfile.user_id == client._hyper_ai_user_id
        ).one()
        assert profile.trading_style is None
        assert profile.risk_preference is None


def test_legacy_sensitive_profile_is_redacted_from_api_and_prompts(tmp_path) -> None:
    client = _build_client(tmp_path)

    with client._hyper_ai_session_factory() as db:
        profile = HyperAiProfile(
            user_id=client._hyper_ai_user_id,
            onboarding_completed=True,
            nickname="api_key=secret-profile-nickname",
            trading_style="Bearer token=secret-token",
            risk_preference="balanced",
            experience_level="private_key=secret-profile-experience",
            preferred_symbols="BTC, ETH",
            preferred_timeframe="15m",
            capital_scale="postgres://provider.example/profile",
        )
        db.add(profile)
        db.commit()

    response = client.get("/api/hyper-ai/profile")
    assert response.status_code == 200
    body = response.json()
    rendered = json.dumps(body, ensure_ascii=False)
    _assert_no_secret_echo(rendered)
    assert body["nickname"] == hyper_ai_service.REDACTED_SENSITIVE_PROFILE_TEXT
    assert body["trading_style"] == hyper_ai_service.REDACTED_SENSITIVE_PROFILE_TEXT
    assert body["experience_level"] == hyper_ai_service.REDACTED_SENSITIVE_PROFILE_TEXT
    assert body["capital_scale"] == hyper_ai_service.REDACTED_SENSITIVE_PROFILE_TEXT
    assert body["risk_preference"] == "balanced"
    assert body["preferred_symbols"] == "BTC, ETH"

    with client._hyper_ai_session_factory() as db:
        profile = db.query(HyperAiProfile).filter(
            HyperAiProfile.user_id == client._hyper_ai_user_id
        ).one()
        profile_context = hyper_ai_service._build_profile_context(profile)
        suggestions_context = hyper_ai_service.get_suggestions_context(
            db,
            user_id=client._hyper_ai_user_id,
        )
        suggestions_prompt = hyper_ai_service.build_suggestions_prompt(suggestions_context)

    for rendered_context in (profile_context, json.dumps(suggestions_context), suggestions_prompt):
        _assert_no_secret_echo(rendered_context)
        assert hyper_ai_service.REDACTED_SENSITIVE_PROFILE_TEXT in rendered_context
    assert "Risk Preference: balanced" in profile_context
    assert "Preferred Symbols: BTC, ETH" in profile_context


def test_onboarding_profile_save_skips_sensitive_fields(tmp_path) -> None:
    client = _build_client(tmp_path)

    with client._hyper_ai_session_factory() as db:
        hyper_ai_service._save_profile_from_onboarding(
            db,
            {
                "nickname": "api_key=secret-profile-nickname",
                "experience": "intermediate",
                "risk": "authorization=Bearer secret-profile-risk",
                "style": "trend following",
            },
            user_id=client._hyper_ai_user_id,
        )
        profile = db.query(HyperAiProfile).filter(
            HyperAiProfile.user_id == client._hyper_ai_user_id
        ).one()
        assert profile.nickname is None
        assert profile.experience_level == "intermediate"
        assert profile.risk_preference is None
        assert profile.trading_style == "trend following"
        assert profile.onboarding_completed is True


def test_hyper_ai_profile_safety_source_guard() -> None:
    with open(hyper_ai_service.__file__, "r", encoding="utf-8") as handle:
        service_source = handle.read()
    import api.hyper_ai_routes as hyper_ai_routes

    with open(hyper_ai_routes.__file__, "r", encoding="utf-8") as handle:
        route_source = handle.read()

    service_forbidden = (
        "parts.append(f\"Trading Style: {profile.trading_style}\")",
        "parts.append(f\"Risk Preference: {profile.risk_preference}\")",
        "profile.nickname = nickname",
        "profile.experience_level = profile_data['experience']",
        "logger.info(f\"Saved onboarding profile:",
        "\"nickname\": profile.nickname",
        "\"trading_style\": profile.trading_style",
    )
    route_forbidden = (
        "\"nickname\": profile.nickname",
        "\"trading_style\": profile.trading_style",
        "profile.trading_style = request.trading_style",
        "profile.risk_preference = request.risk_preference",
        "profile.preferred_symbols = request.preferred_symbols",
        "detail=str(exc)",
    )
    for pattern in service_forbidden:
        assert pattern not in service_source
    for pattern in route_forbidden:
        assert pattern not in route_source
