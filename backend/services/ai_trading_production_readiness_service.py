"""Aggregate no-network production readiness checks for AI Trading V1."""

from __future__ import annotations

import ipaddress
import os
from typing import Any, Dict, Mapping, Optional
from urllib import parse

from sqlalchemy import func

from services import ai_trading_production_handoff_service as handoff_check


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
PLACEHOLDER_HOSTS = {
    "example.com",
    "auth.example.com",
    "casdoor.example.com",
    "localhost",
}
SUPPORTED_AUTH_ALGORITHMS = {"RS256", "RS384", "RS512"}
MODEL_KEY_ENV_NAMES = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "QWEN_API_KEY",
    "DASHSCOPE_API_KEY",
}


def _parse_bool(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: Optional[str], default: float) -> Optional[float]:
    text = str(value if value is not None else default).strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Optional[str], default: int) -> Optional[int]:
    parsed = _parse_float(value, float(default))
    if parsed is None:
        return None
    return int(parsed)


def _csv(value: Optional[str], default: str = "") -> list[str]:
    return [item.strip() for item in str(value if value is not None else default).split(",") if item.strip()]


def _lower_csv(value: Optional[str], default: str = "") -> set[str]:
    return {item.lower() for item in _csv(value, default)}


def load_env(env_file: Optional[str]) -> Dict[str, str]:
    return handoff_check.load_env(env_file)


def _load_env(env_file: Optional[str]) -> Dict[str, str]:
    return load_env(env_file)


def _is_ip_host_private_or_local(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def _sanitized_url_parts(url: str) -> Dict[str, Any]:
    parsed = parse.urlparse(url)
    host = parsed.hostname or ""
    return {
        "scheme": parsed.scheme or None,
        "host": host or None,
        "port": parsed.port,
        "path_present": bool(parsed.path and parsed.path != "/"),
        "query_present": bool(parsed.query),
        "credentials_embedded": bool(parsed.username or parsed.password),
    }


def _build_auth_report(env: Mapping[str, str]) -> Dict[str, Any]:
    require_verified_bearer = _parse_bool(env.get("AUTH_REQUIRE_VERIFIED_BEARER"))
    jwks_url = str(env.get("AUTH_JWKS_URL") or "").strip()
    issuer = str(env.get("AUTH_JWT_ISSUER") or "").strip()
    audiences = _csv(env.get("AUTH_JWT_AUDIENCE"))
    algorithms = set(_csv(env.get("AUTH_JWT_ALGORITHMS"), ""))
    admin_usernames = _lower_csv(env.get("AUTH_ADMIN_USERNAMES"), "default")

    blockers: list[str] = []
    url_parts = _sanitized_url_parts(jwks_url) if jwks_url else {
        "scheme": None,
        "host": None,
        "port": None,
        "path_present": False,
        "query_present": False,
        "credentials_embedded": False,
    }
    host = str(url_parts.get("host") or "").lower()

    if not require_verified_bearer:
        blockers.append("auth_verified_bearer_required")
    if not jwks_url:
        blockers.append("auth_jwks_url_missing")
    else:
        if url_parts["scheme"] != "https":
            blockers.append("auth_jwks_url_must_be_https")
        if host in LOCAL_HOSTS or _is_ip_host_private_or_local(host):
            blockers.append("auth_jwks_url_must_not_be_local_or_private")
        if host in PLACEHOLDER_HOSTS or host.endswith(".example.com"):
            blockers.append("auth_jwks_url_must_not_be_placeholder")
        if url_parts["credentials_embedded"] or url_parts["query_present"]:
            blockers.append("auth_jwks_url_must_not_embed_credentials_or_query")
    if not issuer:
        blockers.append("auth_jwt_issuer_missing")
    if not audiences:
        blockers.append("auth_jwt_audience_missing")
    if not algorithms:
        blockers.append("auth_jwt_algorithms_missing")
    elif not algorithms.issubset(SUPPORTED_AUTH_ALGORITHMS):
        blockers.append("auth_jwt_algorithms_must_be_rs")
    if "default" in admin_usernames:
        blockers.append("auth_default_admin_user_must_be_removed")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "checks": {
            "require_verified_bearer": require_verified_bearer,
            "jwks_url": url_parts,
            "issuer_configured": bool(issuer),
            "audience_count": len(audiences),
            "algorithms": sorted(algorithms),
            "admin_default_user_present": "default" in admin_usernames,
        },
    }


def _build_ai_stream_report(env: Mapping[str, str]) -> Dict[str, Any]:
    global_limit = _parse_int(env.get("AI_STREAM_MAX_RUNNING_GLOBAL"), 12)
    per_user_limit = _parse_int(env.get("AI_STREAM_MAX_RUNNING_PER_USER"), 2)
    task_workers = _parse_int(env.get("AI_TASK_MAX_WORKERS"), 12)
    distributed_admission = _parse_bool(env.get("AI_STREAM_DISTRIBUTED_ADMISSION_ENABLED"))
    distributed_worker = _parse_bool(env.get("AI_STREAM_DISTRIBUTED_WORKER_ENABLED"))
    redis_url_present = bool(str(env.get("AI_STREAM_REDIS_URL") or "").strip())
    fail_open = _parse_bool(env.get("AI_STREAM_DISTRIBUTED_ADMISSION_FAIL_OPEN"))

    blockers: list[str] = []
    warnings: list[str] = []
    if global_limit is None or global_limit <= 0:
        blockers.append("ai_stream_global_limit_required")
    if per_user_limit is None or per_user_limit <= 0:
        blockers.append("ai_stream_per_user_limit_required")
    if task_workers is None or task_workers <= 0:
        blockers.append("ai_stream_worker_limit_required")
    if (
        global_limit is not None
        and per_user_limit is not None
        and global_limit > 0
        and per_user_limit > global_limit
    ):
        blockers.append("ai_stream_per_user_limit_exceeds_global")
    if (distributed_admission or distributed_worker) and not redis_url_present:
        blockers.append("ai_stream_redis_url_required_for_distributed_mode")
    if distributed_admission and fail_open:
        blockers.append("ai_stream_distributed_fail_open_must_be_false")
    if not distributed_admission:
        warnings.append("ai_stream_distributed_admission_disabled_single_server_only")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "checks": {
            "max_running_global": global_limit,
            "max_running_per_user": per_user_limit,
            "task_workers": task_workers,
            "distributed_admission_enabled": distributed_admission,
            "distributed_worker_enabled": distributed_worker,
            "redis_url_present": redis_url_present,
            "distributed_fail_open": fail_open,
        },
    }


def _build_hard_risk_report(env: Mapping[str, str]) -> Dict[str, Any]:
    max_order_notional = _parse_float(env.get("AI_HARD_MAX_ORDER_NOTIONAL_USD"), 0)
    max_leverage = _parse_int(env.get("AI_HARD_MAX_LEVERAGE"), 50)
    single_trade_margin_fraction = _parse_float(
        env.get("AI_HARD_MAX_SINGLE_TRADE_MARGIN_FRACTION"),
        0.5,
    )
    projected_margin_usage = _parse_float(
        env.get("AI_HARD_MAX_PROJECTED_MARGIN_USAGE_PERCENT"),
        75,
    )
    require_stop_loss = _parse_bool(env.get("AI_HARD_REQUIRE_STOP_LOSS"))
    require_take_profit = _parse_bool(env.get("AI_HARD_REQUIRE_TAKE_PROFIT"))

    blockers: list[str] = []
    if max_order_notional is None or max_order_notional <= 0:
        blockers.append("ai_hard_max_order_notional_required")
    if max_leverage is None or max_leverage <= 0 or max_leverage > 50:
        blockers.append("ai_hard_max_leverage_invalid")
    if (
        single_trade_margin_fraction is None
        or single_trade_margin_fraction <= 0
        or single_trade_margin_fraction > 0.5
    ):
        blockers.append("ai_hard_single_trade_margin_fraction_invalid")
    if projected_margin_usage is None or projected_margin_usage <= 0 or projected_margin_usage > 75:
        blockers.append("ai_hard_projected_margin_usage_invalid")
    if not require_stop_loss:
        blockers.append("ai_hard_stop_loss_required")
    if not require_take_profit:
        blockers.append("ai_hard_take_profit_required")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "checks": {
            "max_order_notional_usd": max_order_notional,
            "max_leverage": max_leverage,
            "max_single_trade_margin_fraction": single_trade_margin_fraction,
            "max_projected_margin_usage_percent": projected_margin_usage,
            "require_stop_loss": require_stop_loss,
            "require_take_profit": require_take_profit,
        },
    }


def _build_model_policy_report(env: Mapping[str, str]) -> Dict[str, Any]:
    platform_key_envs_present = sorted(name for name in MODEL_KEY_ENV_NAMES if str(env.get(name) or "").strip())
    warnings = []
    if platform_key_envs_present:
        warnings.append("platform_model_key_env_present_user_profile_keys_preferred")
    return {
        "ready": True,
        "blockers": [],
        "warnings": warnings,
        "checks": {
            "allowed_ai_trading_model_providers": ["deepseek", "qwen"],
            "user_profile_keys_expected": True,
            "platform_model_key_envs_present": platform_key_envs_present,
            "secret_values_returned": False,
        },
    }


def build_handoff_attempt_audit_report(db: Any) -> Dict[str, Any]:
    """Return non-secret admin audit counts for persisted handoff attempts."""
    from database.models import AiTradingSignalHandoffAttemptRecord

    rows = db.query(
        AiTradingSignalHandoffAttemptRecord.result,
        func.count(AiTradingSignalHandoffAttemptRecord.id),
    ).group_by(AiTradingSignalHandoffAttemptRecord.result).all()
    by_result = {str(result or "unknown"): int(count) for result, count in rows}
    total = sum(by_result.values())
    gateway_ready = int(db.query(AiTradingSignalHandoffAttemptRecord).filter(
        AiTradingSignalHandoffAttemptRecord.gateway_ready.is_(True),
    ).count())
    latest_non_submitted = db.query(AiTradingSignalHandoffAttemptRecord).filter(
        AiTradingSignalHandoffAttemptRecord.result.in_(["blocked", "failed"]),
    ).order_by(
        AiTradingSignalHandoffAttemptRecord.created_at.desc(),
        AiTradingSignalHandoffAttemptRecord.id.desc(),
    ).first()

    latest_payload = None
    if latest_non_submitted:
        latest_payload = {
            "id": latest_non_submitted.id,
            "signal_event_id": latest_non_submitted.signal_event_id,
            "strategy_spec_id": latest_non_submitted.strategy_spec_id,
            "symbol": latest_non_submitted.symbol,
            "action": latest_non_submitted.action,
            "result": latest_non_submitted.result,
            "gateway_ready": bool(latest_non_submitted.gateway_ready),
        }

    warnings: list[str] = []
    if by_result.get("failed", 0) > 0:
        warnings.append("handoff_attempt_failed_present")
    if by_result.get("blocked", 0) > 0:
        warnings.append("handoff_attempt_blocked_present")

    return {
        "ready": True,
        "blockers": [],
        "warnings": warnings,
        "checks": {
            "total": total,
            "by_result": by_result,
            "gateway_ready": gateway_ready,
            "gateway_not_ready": max(0, total - gateway_ready),
            "latest_non_submitted": latest_payload,
            "secret_values_returned": False,
        },
    }


def build_report(
    env: Mapping[str, str],
    *,
    require_handoff_approval_flag: bool = True,
    handoff_attempt_audit_report: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    handoff_report = handoff_check.build_report(
        env,
        require_approval_flag=require_handoff_approval_flag,
    )
    auth_report = _build_auth_report(env)
    ai_stream_report = _build_ai_stream_report(env)
    hard_risk_report = _build_hard_risk_report(env)
    model_policy_report = _build_model_policy_report(env)

    component_reports = {
        "auth": auth_report,
        "signal_handoff": {
            "ready": bool(handoff_report.get("production_handoff_ready")),
            "blockers": handoff_report.get("blockers") or [],
            "warnings": handoff_report.get("warnings") or [],
            "checks": handoff_report.get("checks") or {},
        },
        "ai_stream": ai_stream_report,
        "hard_risk": hard_risk_report,
        "model_policy": model_policy_report,
    }
    if handoff_attempt_audit_report is not None:
        component_reports["handoff_audit"] = {
            "ready": bool(handoff_attempt_audit_report.get("ready", True)),
            "blockers": list(handoff_attempt_audit_report.get("blockers") or []),
            "warnings": list(handoff_attempt_audit_report.get("warnings") or []),
            "checks": dict(handoff_attempt_audit_report.get("checks") or {}),
        }

    blockers: list[str] = []
    warnings: list[str] = []
    for component, report in component_reports.items():
        for blocker in report.get("blockers") or []:
            blockers.append(f"{component}:{blocker}")
        for warning in report.get("warnings") or []:
            warnings.append(f"{component}:{warning}")

    return {
        "production_ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "checks": component_reports,
        "next_actions": [
            "Configure verified Bearer JWT auth with HTTPS JWKS, issuer, audience, and RS algorithms.",
            "Configure the real HTTPS order-backend signal gateway and run the production handoff checker.",
            "Set platform hard-risk caps for max notional, leverage, margin usage, stop loss, and take profit.",
            "For multiple backend instances, enable Redis-backed AI stream admission and keep fail-open disabled.",
            "Keep AI Trading model keys user-provided through Hyper AI profiles; do not put user keys in model context.",
        ],
    }
