import json
import logging

from services import ai_context_compression_service as compression_service


class ResponseStub:
    def __init__(self, status_code: int, body: bytes = b""):
        self.status_code = status_code
        self.content = body

    def json(self):
        return {}


class DbStub:
    pass


class BackgroundDbStub:
    def close(self):
        return None


def _api_config() -> dict:
    return {
        "base_url": "https://provider.example/v1",
        "api_key": "sk-test",
        "model": "qwen-plus",
        "api_format": "openai",
    }


def _messages() -> list[dict]:
    return [
        {"role": "user", "content": "older trading context"},
        {"role": "assistant", "content": "newer trading context"},
    ]


def _assert_no_secret_echo(text: str) -> None:
    rendered = text.lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "postgres://" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "token=" not in rendered
    assert "provider.example" not in rendered
    assert "apikeysecretcompressionerror" not in rendered


def _capture_system_logs(monkeypatch) -> list[dict]:
    captured: list[dict] = []

    def fake_add_log(level, category, message, details=None):
        captured.append(
            {
                "level": level,
                "category": category,
                "message": message,
                "details": details or {},
            }
        )

    monkeypatch.setattr(compression_service.system_logger, "add_log", fake_add_log)
    return captured


def test_generate_summary_provider_failure_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.ERROR, logger=compression_service.__name__)
    system_logs = _capture_system_logs(monkeypatch)

    def failing_post(*args, **kwargs):
        return ResponseStub(
            401,
            b"api_key=secret Bearer token=abc postgres://provider.example/db",
        )

    monkeypatch.setattr(compression_service.requests, "post", failing_post)

    summary = compression_service.generate_summary(_messages(), _api_config())

    assert summary is None
    assert "Compression API error: status=401" in caplog.text
    assert "response_body_present=True" in caplog.text
    _assert_no_secret_echo(caplog.text)
    rendered_logs = json.dumps(system_logs, ensure_ascii=False)
    assert "response_body_present" in rendered_logs
    _assert_no_secret_echo(rendered_logs)


def test_generate_summary_connection_error_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.ERROR, logger=compression_service.__name__)
    system_logs = _capture_system_logs(monkeypatch)

    def connection_error_post(*args, **kwargs):
        raise compression_service.requests.exceptions.ConnectionError(
            "api_key=secret Bearer token=abc postgres://provider.example/db"
        )

    monkeypatch.setattr(compression_service.requests, "post", connection_error_post)

    summary = compression_service.generate_summary(_messages(), _api_config())

    assert summary is None
    assert "Compression failed" in caplog.text
    _assert_no_secret_echo(caplog.text)
    rendered_logs = json.dumps(system_logs, ensure_ascii=False)
    assert "Compression exception" in rendered_logs
    _assert_no_secret_echo(rendered_logs)


def test_background_memory_extraction_start_failure_logs_are_safe(monkeypatch, caplog) -> None:
    caplog.set_level(logging.WARNING, logger=compression_service.__name__)

    monkeypatch.setattr(compression_service, "should_compress", lambda messages, model: (True, 100, 20))
    monkeypatch.setattr(compression_service, "find_compression_point", lambda messages, target_tokens: 1)
    monkeypatch.setattr(compression_service, "generate_summary", lambda messages, api_config: "safe summary")

    def failing_submit(*args, **kwargs):
        raise RuntimeError("api_key=secret Bearer token=abc postgres://provider.example/db")

    monkeypatch.setattr(compression_service, "submit_ai_background_task", failing_submit)

    result = compression_service.compress_messages(
        _messages(),
        _api_config(),
        db=DbStub(),
        user_id=7,
    )

    assert result["compressed"] is True
    assert result["summary"] == "safe summary"
    assert "[Compression] Failed to start memory extraction thread" in caplog.text
    _assert_no_secret_echo(caplog.text)


def test_background_memory_extraction_runtime_failure_logs_are_safe(monkeypatch, caplog) -> None:
    import database.connection as db_connection
    from services import hyper_ai_memory_service

    caplog.set_level(logging.WARNING, logger=compression_service.__name__)

    monkeypatch.setattr(compression_service, "should_compress", lambda messages, model: (True, 100, 20))
    monkeypatch.setattr(compression_service, "find_compression_point", lambda messages, target_tokens: 1)
    monkeypatch.setattr(compression_service, "generate_summary", lambda messages, api_config: "safe summary")
    monkeypatch.setattr(db_connection, "SessionLocal", lambda: BackgroundDbStub())

    def failing_memory_processor(*args, **kwargs):
        raise RuntimeError("api_key=secret Bearer token=abc postgres://provider.example/db")

    def immediate_submit(fn, *args, **kwargs):
        fn(*args, **kwargs)

    monkeypatch.setattr(hyper_ai_memory_service, "process_compression_memories", failing_memory_processor)
    monkeypatch.setattr(compression_service, "submit_ai_background_task", immediate_submit)

    result = compression_service.compress_messages(
        _messages(),
        _api_config(),
        db=DbStub(),
        user_id=7,
    )

    assert result["compressed"] is True
    assert result["summary"] == "safe summary"
    assert "[Compression] Background memory extraction failed" in caplog.text
    _assert_no_secret_echo(caplog.text)


def test_ai_context_compression_error_source_guard() -> None:
    with open(compression_service.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    forbidden = (
        "response.text",
        "response_snippet",
        '"endpoint": endpoint',
        "endpoint={endpoint}",
        "Compression failed: {type(e).__name__}: {e}",
        "Compression exception: {type(e).__name__}",
        '"error": str(e)',
        "Background memory extraction failed: {type(e).__name__}: {e}",
        "Failed to start memory extraction thread: {e}",
    )
    for pattern in forbidden:
        assert pattern not in source
