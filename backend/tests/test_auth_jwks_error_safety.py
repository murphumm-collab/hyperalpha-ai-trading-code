import ast
import json
from pathlib import Path

from fastapi import HTTPException

from api import auth_utils


def _assert_no_secret_echo(payload) -> None:
    rendered = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in rendered
    assert "bearer" not in rendered
    assert "token=" not in rendered
    assert "private_key" not in rendered
    assert "secret" not in rendered
    assert "auth.internal" not in rendered


def _reset_jwks_cache() -> None:
    auth_utils._JWKS_CACHE.update({"url": None, "expires_at": 0, "keys": []})


def test_jwks_fetch_disables_redirects_and_returns_fixed_public_error(monkeypatch) -> None:
    _reset_jwks_cache()
    requests_seen = []

    def failing_get(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        raise RuntimeError("Bearer token=secret private_key=secret https://auth.internal/jwks")

    monkeypatch.setattr(auth_utils.requests, "get", failing_get)

    try:
        auth_utils._get_jwks_keys("https://auth.hyperalpha.org/.well-known/jwks.json")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Unable to fetch JWKS"
        _assert_no_secret_echo({"detail": exc.detail})
    else:
        raise AssertionError("Expected JWKS fetch failure")

    assert requests_seen
    assert requests_seen[0]["kwargs"]["allow_redirects"] is False


def test_jwks_fetch_success_uses_no_redirects_and_caches_keys(monkeypatch) -> None:
    _reset_jwks_cache()
    requests_seen = []

    class ResponseStub:
        def raise_for_status(self):
            pass

        def json(self):
            return {"keys": [{"kid": "key-1", "kty": "RSA", "alg": "RS256"}]}

    def successful_get(*args, **kwargs):
        requests_seen.append({"args": args, "kwargs": kwargs})
        return ResponseStub()

    monkeypatch.setattr(auth_utils.requests, "get", successful_get)

    result = auth_utils._get_jwks_keys("https://auth.hyperalpha.org/.well-known/jwks.json")
    cached = auth_utils._get_jwks_keys("https://auth.hyperalpha.org/.well-known/jwks.json")

    assert result == [{"kid": "key-1", "kty": "RSA", "alg": "RS256"}]
    assert cached == result
    assert len(requests_seen) == 1
    assert requests_seen[0]["kwargs"]["allow_redirects"] is False


def test_auth_jwks_error_safety_source_guard() -> None:
    source = Path(auth_utils.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "requests.get(jwks_url, timeout=10)" not in source
    assert "Unable to fetch JWKS" in source

    request_gets = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "requests"
    ]
    assert request_gets
    for call in request_gets:
        allow_redirects = [
            keyword.value
            for keyword in call.keywords
            if keyword.arg == "allow_redirects"
        ]
        assert allow_redirects
        assert isinstance(allow_redirects[0], ast.Constant)
        assert allow_redirects[0].value is False
