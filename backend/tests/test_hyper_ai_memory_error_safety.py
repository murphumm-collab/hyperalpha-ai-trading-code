import json
import logging

from services import hyper_ai_memory_service


class ResponseStub:
    def __init__(self, status_code: int, body: bytes = b"", payload: dict | None = None):
        self.status_code = status_code
        self.content = body
        self._payload = payload or {}

    def json(self):
        return self._payload


def _assert_no_secret_echo(text: str) -> None:
    rendered = text.lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "postgres://" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "token=" not in rendered
    assert "provider.example" not in rendered
    assert "apikeysecretmemoryerror" not in rendered


def _api_config() -> dict:
    return {
        "base_url": "https://provider.example/v1",
        "api_key": "sk-test",
        "model": "qwen-plus",
        "api_format": "openai",
    }


def test_memory_extraction_redacts_sensitive_conversation_and_filters_output(monkeypatch) -> None:
    captured: dict = {}

    def successful_post(*args, **kwargs):
        captured["body"] = kwargs.get("json", {})
        return ResponseStub(
            200,
            payload={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "memories": [
                                        {
                                            "category": "risk_memory",
                                            "content": "Use max loss 2% on BTC",
                                            "importance": 0.9,
                                        },
                                        {
                                            "category": "execution_memory",
                                            "content": "authorization=Bearer secret-memory-output",
                                            "importance": 0.9,
                                        },
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(hyper_ai_memory_service.requests, "post", successful_post)

    result = hyper_ai_memory_service.extract_memories_from_conversation(
        (
            "Keep BTC risk low. api_key=secret-user-key "
            "Bearer token=secret-token postgres://provider.example/db"
        ),
        _api_config(),
    )

    assert result == [
        {
            "category": "risk_memory",
            "content": "Use max loss 2% on BTC",
            "importance": 0.9,
        }
    ]
    rendered_body = json.dumps(captured["body"], ensure_ascii=False)
    assert "api_key" not in rendered_body.lower()
    assert "secret-user-key" not in rendered_body
    assert "secret-token" not in rendered_body
    assert "postgres://provider.example/db" not in rendered_body
    assert "[redacted_sensitive_memory_text]" in rendered_body


def test_memory_dedup_redacts_prompt_and_refuses_sensitive_merge(monkeypatch) -> None:
    captured: dict = {}
    updates: list[dict] = []
    adds: list[dict] = []

    monkeypatch.setattr(
        hyper_ai_memory_service,
        "get_memories",
        lambda *args, **kwargs: [
            {
                "id": 1,
                "category": "risk_memory",
                "content": "api_key=legacy-existing-secret",
                "importance": 0.6,
            }
        ],
    )
    monkeypatch.setattr(hyper_ai_memory_service, "enforce_memory_limit", lambda *args, **kwargs: 0)

    def fake_add_memory(db, category, content, source="conversation", importance=0.5, user_id=None):
        adds.append({"category": category, "content": content, "importance": importance, "user_id": user_id})
        return object()

    def fake_update_memory(db, memory_id, content=None, importance=None, is_active=None, user_id=None):
        updates.append({"id": memory_id, "content": content, "importance": importance, "user_id": user_id})
        return object()

    monkeypatch.setattr(hyper_ai_memory_service, "add_memory", fake_add_memory)
    monkeypatch.setattr(hyper_ai_memory_service, "update_memory", fake_update_memory)

    def successful_post(*args, **kwargs):
        captured["body"] = kwargs.get("json", {})
        return ResponseStub(
            200,
            payload={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "actions": [
                                        {
                                            "new_index": 0,
                                            "action": "UPDATE",
                                            "existing_id": 1,
                                            "merged": "authorization=Bearer secret-merge",
                                        },
                                        {"new_index": 1, "action": "ADD"},
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(hyper_ai_memory_service.requests, "post", successful_post)

    count = hyper_ai_memory_service.batch_dedup_memories(
        object(),
        [
            {"category": "risk_memory", "content": "Use max loss 2% on BTC", "importance": 0.9},
            {"category": "execution_memory", "content": "token=secret-new-memory", "importance": 0.8},
        ],
        _api_config(),
        user_id=7,
    )

    assert count == 1
    assert adds == []
    assert updates == [{"id": 1, "content": "Use max loss 2% on BTC", "importance": 0.9, "user_id": 7}]
    rendered_body = json.dumps(captured["body"], ensure_ascii=False)
    assert "api_key" not in rendered_body.lower()
    assert "legacy-existing-secret" not in rendered_body
    assert "token=secret-new-memory" not in rendered_body
    assert "[redacted_sensitive_memory_text]" in rendered_body


def test_memory_dedup_provider_failure_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.WARNING, logger=hyper_ai_memory_service.__name__)

    def failing_post(*args, **kwargs):
        return ResponseStub(
            401,
            b"api_key=secret Bearer token=abc postgres://provider.example/db",
        )

    monkeypatch.setattr(hyper_ai_memory_service.requests, "post", failing_post)

    result = hyper_ai_memory_service._call_llm_for_dedup(
        "Summarize user memory", _api_config()
    )

    assert result is None
    assert "[Memory] Dedup API error: status=401 response_body_present=True" in caplog.text
    _assert_no_secret_echo(caplog.text)


def test_memory_extraction_provider_failure_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.WARNING, logger=hyper_ai_memory_service.__name__)

    def failing_post(*args, **kwargs):
        return ResponseStub(
            503,
            b"api_key=secret Bearer token=abc postgres://provider.example/db",
        )

    monkeypatch.setattr(hyper_ai_memory_service.requests, "post", failing_post)

    result = hyper_ai_memory_service.extract_memories_from_conversation(
        [{"role": "user", "content": "remember my risk limit"}],
        _api_config(),
    )

    assert result == []
    assert "[Memory] Extraction API error: status=503 response_body_present=True" in caplog.text
    _assert_no_secret_echo(caplog.text)


def test_memory_dedup_invalid_model_text_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.WARNING, logger=hyper_ai_memory_service.__name__)

    def invalid_json_post(*args, **kwargs):
        return ResponseStub(
            200,
            payload={
                "choices": [
                    {
                        "message": {
                            "content": (
                                "api_key=secret Bearer token=abc "
                                "postgres://provider.example/db"
                            )
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(hyper_ai_memory_service.requests, "post", invalid_json_post)

    result = hyper_ai_memory_service._call_llm_for_dedup(
        "Summarize user memory", _api_config()
    )

    assert result is None
    assert "[Memory] Dedup response not valid JSON" in caplog.text
    _assert_no_secret_echo(caplog.text)


def test_memory_extraction_connection_error_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.WARNING, logger=hyper_ai_memory_service.__name__)

    def connection_error_post(*args, **kwargs):
        raise hyper_ai_memory_service.requests.exceptions.ConnectionError(
            "api_key=secret Bearer token=abc postgres://provider.example/db"
        )

    monkeypatch.setattr(hyper_ai_memory_service.requests, "post", connection_error_post)

    result = hyper_ai_memory_service.extract_memories_from_conversation(
        [{"role": "user", "content": "compress this context"}],
        _api_config(),
    )

    assert result == []
    assert "[Memory] Extraction API connection error" in caplog.text
    _assert_no_secret_echo(caplog.text)


def test_hyper_ai_memory_error_source_guard() -> None:
    with open(hyper_ai_memory_service.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    forbidden = (
        "conversation=conversation_text[:6000]",
        "f\"[ID:{m['id']}] ({m['category']}) {m['content']}\"",
        "f\"[{i}] ({m.get('category','context')}) {m.get('content','')}\"",
        "update_memory(db, eid, content=merged",
        "body={response.text",
        "response.text[:",
        "Dedup response not valid JSON: {text",
        "Dedup API connection error: {e}",
        "Dedup response JSON parse error: {e}",
        "Dedup unexpected error: {type(e).__name__}: {e}",
        "Extraction API error: status={response.status_code}",
        "Extraction API connection error: {e}",
        "Extraction response JSON parse error: {e}",
        "Extraction unexpected error: {type(e).__name__}: {e}",
    )
    for pattern in forbidden:
        assert pattern not in source
