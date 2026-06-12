import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth_utils import get_authenticated_user_dependency, get_current_user_dependency
from api.hyper_ai_routes import router
from database.connection import Base, get_db
from database.models import HyperAiProfile, User
from services import hyper_ai_service


def _build_client(tmp_path):
    db_path = tmp_path / "hyper_ai_llm_base_url_safety.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    user = User(username="llm-base-url-safety-user", is_active="true")
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
    user_context = lambda: SimpleNamespace(id=user_id)
    app.dependency_overrides[get_current_user_dependency] = user_context
    app.dependency_overrides[get_authenticated_user_dependency] = user_context
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
    assert "secret-llm-base" not in rendered
    assert "token=secret" not in rendered


def test_profile_llm_rejects_sensitive_base_url_without_network_or_echo(monkeypatch, tmp_path) -> None:
    client = _build_client(tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("connection test should not run for rejected base_url")

    import api.hyper_ai_routes as hyper_ai_routes

    monkeypatch.setattr(hyper_ai_routes, "test_llm_connection", fail_if_called)

    response = client.post(
        "/api/hyper-ai/profile/llm",
        json={
            "provider": "custom",
            "api_key": "test-key",
            "model": "qwen-test",
            "base_url": "https://llm.example.test/v1?api_key=secret-llm-base-url",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": hyper_ai_service.SENSITIVE_LLM_BASE_URL_ERROR}
    _assert_no_secret_echo(response.text)

    with client._hyper_ai_session_factory() as db:
        profile = db.query(HyperAiProfile).filter(
            HyperAiProfile.user_id == client._hyper_ai_user_id
        ).one_or_none()
        assert profile is None or profile.llm_base_url is None


def test_test_connection_rejects_sensitive_base_url_without_network_or_echo(monkeypatch, tmp_path) -> None:
    client = _build_client(tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("connection test should not run for rejected base_url")

    import api.hyper_ai_routes as hyper_ai_routes

    monkeypatch.setattr(hyper_ai_routes, "test_llm_connection", fail_if_called)

    response = client.post(
        "/api/hyper-ai/test-connection",
        json={
            "provider": "custom",
            "api_key": "test-key",
            "model": "qwen-test",
            "base_url": "https://token:secret-llm-base-url@llm.example.test/v1",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": hyper_ai_service.SENSITIVE_LLM_BASE_URL_ERROR}
    _assert_no_secret_echo(response.text)


def test_legacy_sensitive_base_url_is_redacted_and_blocked(tmp_path) -> None:
    client = _build_client(tmp_path)

    with client._hyper_ai_session_factory() as db:
        profile = HyperAiProfile(
            user_id=client._hyper_ai_user_id,
            llm_provider="custom",
            llm_model="qwen-test",
            llm_base_url="https://token:secret-llm-base-url@llm.example.test/v1",
        )
        db.add(profile)
        db.commit()

    response = client.get("/api/hyper-ai/profile")
    assert response.status_code == 200
    body = response.json()
    rendered = json.dumps(body, ensure_ascii=False)
    _assert_no_secret_echo(rendered)
    assert body["llm_configured"] is False
    assert body["llm_base_url"] == hyper_ai_service.REDACTED_SENSITIVE_LLM_BASE_URL

    with client._hyper_ai_session_factory() as db:
        config = hyper_ai_service.get_llm_config(db, user_id=client._hyper_ai_user_id)

    rendered_config = json.dumps(config, ensure_ascii=False)
    _assert_no_secret_echo(rendered_config)
    assert config["configured"] is False
    assert config["base_url_blocked"] is True
    assert config["base_url"] == hyper_ai_service.REDACTED_SENSITIVE_LLM_BASE_URL


def test_valid_llm_base_url_is_preserved_for_storage() -> None:
    assert (
        hyper_ai_service.validate_llm_base_url_for_storage(" https://llm.example.test/v1 ")
        == "https://llm.example.test/v1"
    )
    assert (
        hyper_ai_service.sanitize_llm_base_url_for_response("https://llm.example.test/v1")
        == "https://llm.example.test/v1"
    )


def test_hyper_ai_llm_base_url_safety_source_guard() -> None:
    with open(hyper_ai_service.__file__, "r", encoding="utf-8") as handle:
        service_source = handle.read()
    import api.hyper_ai_routes as hyper_ai_routes

    with open(hyper_ai_routes.__file__, "r", encoding="utf-8") as handle:
        route_source = handle.read()

    service_forbidden = (
        "profile.llm_base_url = base_url",
    )
    route_forbidden = (
        "base_url=request.base_url",
    )
    for pattern in service_forbidden:
        assert pattern not in service_source
    for pattern in route_forbidden:
        assert pattern not in route_source
