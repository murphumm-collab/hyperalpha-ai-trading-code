import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth_utils import get_current_user_dependency
from api.hyper_ai_routes import router
from database.connection import Base, get_db
from database.models import HyperAiConversation, HyperAiMessage, User
from services import hyper_ai_service


def _build_client(tmp_path):
    db_path = tmp_path / "hyper_ai_suggestions_context_safety.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    db = Session()
    user = User(username="suggestions-context-safety-user", is_active="true")
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
    assert "secret-suggestion" not in rendered
    assert "sk-secret" not in rendered


def test_user_message_secret_is_not_used_as_conversation_title(tmp_path) -> None:
    client = _build_client(tmp_path)

    with client._hyper_ai_session_factory() as db:
        conversation = hyper_ai_service.get_or_create_conversation(
            db,
            user_id=client._hyper_ai_user_id,
        )
        hyper_ai_service.save_message(
            db,
            conversation.id,
            "user",
            "api_key=secret-suggestion-title please build a BTC strategy",
            user_id=client._hyper_ai_user_id,
        )
        db.refresh(conversation)
        assert conversation.title == hyper_ai_service.REDACTED_SENSITIVE_CONVERSATION_TEXT

    response = client.get("/api/hyper-ai/conversations")
    assert response.status_code == 200
    rendered = json.dumps(response.json(), ensure_ascii=False)
    _assert_no_secret_echo(rendered)
    assert hyper_ai_service.REDACTED_SENSITIVE_CONVERSATION_TEXT in rendered


def test_legacy_sensitive_conversation_context_is_redacted_from_suggestions(tmp_path) -> None:
    client = _build_client(tmp_path)

    with client._hyper_ai_session_factory() as db:
        conversation = HyperAiConversation(
            user_id=client._hyper_ai_user_id,
            title="Bearer secret-suggestion-title",
            is_onboarding=False,
            is_bot_conversation=False,
            message_count=3,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        db.add_all(
            [
                HyperAiMessage(
                    conversation_id=conversation.id,
                    role="user",
                    content="postgres://secret-suggestion-db.example/trading",
                ),
                HyperAiMessage(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="Use a safe BTC breakout filter.",
                ),
                HyperAiMessage(
                    conversation_id=conversation.id,
                    role="user",
                    content="private_key=secret-suggestion-wallet",
                ),
            ]
        )
        db.commit()

    response = client.get("/api/hyper-ai/conversations")
    assert response.status_code == 200
    rendered_response = json.dumps(response.json(), ensure_ascii=False)
    _assert_no_secret_echo(rendered_response)
    assert hyper_ai_service.REDACTED_SENSITIVE_CONVERSATION_TEXT in rendered_response

    with client._hyper_ai_session_factory() as db:
        context = hyper_ai_service.get_suggestions_context(
            db,
            user_id=client._hyper_ai_user_id,
        )
        prompt = hyper_ai_service.build_suggestions_prompt(context)

    rendered_context = json.dumps(context, ensure_ascii=False)
    _assert_no_secret_echo(rendered_context)
    _assert_no_secret_echo(prompt)
    assert hyper_ai_service.REDACTED_SENSITIVE_CONVERSATION_TEXT in rendered_context
    assert hyper_ai_service.REDACTED_SENSITIVE_CONVERSATION_TEXT in prompt
    assert "Use a safe BTC breakout filter." in prompt


def test_build_suggestions_prompt_resanitizes_external_context() -> None:
    context = {
        "profile": {},
        "config_status": {"trader_count": 1, "signal_pool_count": 0, "wallet_count": 0},
        "conversations": [
            {
                "title": "sk-secret-suggestion-title",
                "snippets": [
                    "- User: api_key=secret-suggestion-inline",
                    "- AI: Safe visible response",
                ],
            }
        ],
    }

    prompt = hyper_ai_service.build_suggestions_prompt(context)

    _assert_no_secret_echo(prompt)
    assert hyper_ai_service.REDACTED_SENSITIVE_CONVERSATION_TEXT in prompt
    assert "Safe visible response" in prompt


def test_hyper_ai_suggestions_context_safety_source_guard() -> None:
    with open(hyper_ai_service.__file__, "r", encoding="utf-8") as handle:
        service_source = handle.read()
    import api.hyper_ai_routes as hyper_ai_routes

    with open(hyper_ai_routes.__file__, "r", encoding="utf-8") as handle:
        route_source = handle.read()

    service_forbidden = (
        'conv.title = content[:50] + ("..." if len(content) > 50 else "")',
        '"title": conv.title',
        'content = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content',
        "prompt_parts.append(f\"\\n[{conv['title']}]\")",
        'logger.info(f"[Suggestions] Calling LLM: {endpoint}, model: {model}")',
        'logger.info(f"Updated suggested questions: {questions}")',
    )
    route_forbidden = (
        '"title": c.title',
    )
    for pattern in service_forbidden:
        assert pattern not in service_source
    for pattern in route_forbidden:
        assert pattern not in route_source
