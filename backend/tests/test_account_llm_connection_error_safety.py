import ast
import json

import requests

from api import account_routes


class ResponseStub:
    def __init__(self, status_code: int, body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text

    def json(self):
        return self._body


def _payload(**overrides) -> dict:
    payload = {
        "model": "qwen-plus",
        "base_url": "https://provider.example/v1",
        "api_key": "sk-test",
    }
    payload.update(overrides)
    return payload


def _assert_no_secret_echo(payload: dict) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "postgres://" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "token=" not in rendered
    assert "provider.example" not in rendered
    assert "llm.internal" not in rendered


def test_account_llm_connection_error_does_not_echo_endpoint_or_exception(monkeypatch) -> None:
    captured_kwargs: list[dict] = []

    def failing_post(*args, **kwargs):
        captured_kwargs.append(kwargs)
        raise requests.ConnectionError(
            "api_key=secret Bearer token=secret https://llm.internal/v1 postgres://provider.example/db"
        )

    monkeypatch.setattr(requests, "post", failing_post)

    result = account_routes.test_llm_connection(
        _payload(base_url="https://token:secret@provider.example/v1?api_key=secret"),
        current_user=object(),
    )

    assert result == {
        "success": False,
        "message": account_routes.SAFE_LLM_CONNECTION_TEST_FAILED_MESSAGE,
    }
    assert captured_kwargs
    assert all(kwargs.get("allow_redirects") is False for kwargs in captured_kwargs)
    _assert_no_secret_echo(result)


def test_account_llm_request_exception_uses_fixed_public_error_label(monkeypatch) -> None:
    def failing_post(*args, **kwargs):
        raise requests.RequestException(
            "provider body includes api_key=secret Bearer token=secret https://provider.example/v1"
        )

    monkeypatch.setattr(requests, "post", failing_post)

    result = account_routes.test_llm_connection(_payload(), current_user=object())

    assert result == {
        "success": False,
        "message": account_routes.SAFE_LLM_CONNECTION_TEST_FAILED_MESSAGE,
    }
    _assert_no_secret_echo(result)


def test_account_llm_provider_failure_body_is_not_returned_to_frontend(monkeypatch) -> None:
    def failing_post(*args, **kwargs):
        return ResponseStub(
            500,
            {"error": {"message": "api_key=secret Bearer token=secret https://provider.example/v1"}},
            text="api_key=secret Bearer token=secret postgres://provider.example/db",
        )

    monkeypatch.setattr(requests, "post", failing_post)

    result = account_routes.test_llm_connection(_payload(), current_user=object())

    assert result == {
        "success": False,
        "message": f"API returned status 500: {account_routes.SAFE_LLM_CONNECTION_TEST_FAILED_MESSAGE}",
    }
    _assert_no_secret_echo(result)


def test_account_llm_404_does_not_echo_user_supplied_model(monkeypatch) -> None:
    def not_found_post(*args, **kwargs):
        return ResponseStub(404, text="model api_key=secret missing")

    monkeypatch.setattr(requests, "post", not_found_post)

    result = account_routes.test_llm_connection(
        _payload(
            base_url="https://provider.example/v1/chat/completions",
            model="qwen-plus token=secret provider.example",
        ),
        current_user=object(),
    )

    assert result == {
        "success": False,
        "message": "Model not found or endpoint not available.",
    }
    _assert_no_secret_echo(result)


def test_account_llm_connection_error_safety_source_guard() -> None:
    with open(account_routes.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()

    forbidden = (
        "Failed to connect to {ep}",
        "Failed to connect to {base_url}",
        "Connection test failed: {str(",
        "Failed to test LLM connection: {str(",
        "API returned status {response.status_code}: {response.text}",
        "response.text",
        "full_message={message}",
    )
    for pattern in forbidden:
        assert pattern not in source


def test_account_routes_disable_redirects_for_requests_post() -> None:
    with open(account_routes.__file__, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read())

    missing_lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "post":
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "requests":
            continue
        has_redirect_guard = any(
            keyword.arg == "allow_redirects"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in node.keywords
        )
        if not has_redirect_guard:
            missing_lines.append(node.lineno)

    assert missing_lines == []
