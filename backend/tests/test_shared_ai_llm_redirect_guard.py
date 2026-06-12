import ast

from services import ai_attribution_service
from services import ai_decision_service
from services import ai_program_service
from services import ai_prompt_generation_service
from services import ai_signal_generation_service
from services import kline_ai_analysis_service
from services import prompt_backtest_service


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
