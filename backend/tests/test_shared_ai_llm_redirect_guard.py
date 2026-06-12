import ast

from api import account_routes
from services import ai_attribution_service
from services import ai_decision_service
from services import ai_program_service
from services import ai_prompt_generation_service
from services import ai_signal_generation_service
from services import kline_ai_analysis_service
from services import news_ai_classifier
from services import prompt_backtest_service
from services.llm_transport_security import (
    LLM_ALLOW_INSECURE_TLS_ENV,
    llm_tls_verify_enabled,
)


def _requests_post_lines_missing_redirect_guard(module) -> list[int]:
    with open(module.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)
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
    return missing_lines


def _lines_with_literal_verify_false(module) -> list[int]:
    with open(module.__file__, "r", encoding="utf-8") as handle:
        source = handle.read()
    tree = ast.parse(source)
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "verify"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is False
            ):
                lines.append(node.lineno)
    return lines


def test_shared_ai_services_disable_redirects_for_requests_post() -> None:
    modules = (
        ai_attribution_service,
        ai_decision_service,
        ai_program_service,
        ai_prompt_generation_service,
        ai_signal_generation_service,
        kline_ai_analysis_service,
        prompt_backtest_service,
    )

    missing = {
        module.__name__: lines
        for module in modules
        if (lines := _requests_post_lines_missing_redirect_guard(module))
    }

    assert missing == {}


def test_shared_ai_services_do_not_disable_tls_verification_by_default() -> None:
    modules = (
        account_routes,
        ai_decision_service,
        kline_ai_analysis_service,
        news_ai_classifier,
        prompt_backtest_service,
    )

    insecure = {
        module.__name__: lines
        for module in modules
        if (lines := _lines_with_literal_verify_false(module))
    }

    assert insecure == {}


def test_llm_tls_verification_requires_explicit_local_override(monkeypatch) -> None:
    monkeypatch.delenv(LLM_ALLOW_INSECURE_TLS_ENV, raising=False)
    assert llm_tls_verify_enabled() is True

    monkeypatch.setenv(LLM_ALLOW_INSECURE_TLS_ENV, "true")
    assert llm_tls_verify_enabled() is False

    monkeypatch.setenv(LLM_ALLOW_INSECURE_TLS_ENV, "false")
    assert llm_tls_verify_enabled() is True
