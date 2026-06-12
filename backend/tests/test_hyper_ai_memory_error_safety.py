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
