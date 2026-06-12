import json

from services import hyper_ai_service


class ResponseStub:
    def __init__(self, status_code: int, body: bytes = b""):
        self.status_code = status_code
        self.content = body

    def iter_lines(self):
        return iter(())


def _event_payload(raw_event: str) -> dict:
    for line in raw_event.splitlines():
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError(f"No data line in event: {raw_event!r}")


def _assert_no_secret_echo(payload: dict) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "postgres://" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "token=" not in rendered
    assert "provider.example" not in rendered


def test_llm_connection_test_redacts_provider_failure_body(monkeypatch) -> None:
    def failing_post(*args, **kwargs):
        return ResponseStub(
            401,
            b'{"error":{"message":"api_key=secret Bearer token postgres://provider.example/db"}}',
        )

    monkeypatch.setattr(hyper_ai_service.requests, "post", failing_post)

    payload = hyper_ai_service.test_llm_connection(
        provider="deepseek",
        api_key="sk-test",
        model="deepseek-v4-flash",
    )

    assert payload["success"] is False
    assert payload["error_code"] == "hyper_ai_llm_connection_test_failed"
    assert payload["status"] == 401
    _assert_no_secret_echo(payload)


def test_insight_stream_provider_failure_uses_safe_error_event(monkeypatch) -> None:
    monkeypatch.setattr(
        hyper_ai_service,
        "get_llm_config",
        lambda db, user_id=None: {
            "configured": True,
            "base_url": "https://provider.example/v1",
            "model": "deepseek-v4-flash",
            "api_key": "sk-test",
            "api_format": "openai",
        },
    )

    def failing_post(*args, **kwargs):
        return ResponseStub(
            401,
            b"api_key=secret Bearer token postgres://provider.example/db",
        )

    monkeypatch.setattr(hyper_ai_service.requests, "post", failing_post)

    events = list(
        hyper_ai_service.stream_insight_response(
            db=object(),
            context={"symbol": "BTC"},
            user_id=7,
        )
    )

    payload = _event_payload(events[-1])
    assert payload == {
        "message": "Hyper AI provider request failed. Please retry later.",
        "error_code": "hyper_ai_provider_request_failed",
        "status": 401,
    }
    _assert_no_secret_echo(payload)


def test_hyper_ai_service_error_source_guard() -> None:
    with open(hyper_ai_service.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    forbidden = (
        'yield format_sse_event("error", {"message": str(e)})',
        '"error": str(e)',
        '"message": str(e)',
        "Connection failed: {str(e)",
        "return {\"success\": False, \"error\": str(e)",
        "Failed to parse response: {e}",
        "[Error during processing] {str(e)}",
        'interrupt_reason = f"Error: {str(e)}"',
        "response={last_response_text",
        "last_response_text",
        "response.text[:",
    )
    for pattern in forbidden:
        assert pattern not in source

    assert "SAFE_HYPER_AI_PROVIDER_REQUEST_FAILED_MESSAGE" in source
    assert "_safe_hyper_ai_provider_failure_event" in source
