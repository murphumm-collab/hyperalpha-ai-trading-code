"""No-network production readiness checks for AI Trading signal handoff."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib import parse


APPROVAL_ENV = "AI_TRADING_PRODUCTION_HANDOFF_APPROVED"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
PLACEHOLDER_HOSTS = {
    "example.com",
    "order-backend.example.com",
    "localhost",
}


def _parse_bool(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: Optional[str], default: float) -> Optional[float]:
    text = str(value if value is not None else default).strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_env(env_file: Optional[str]) -> Dict[str, str]:
    env = dict(os.environ)
    if env_file:
        env.update(_parse_env_file(Path(env_file)))
    return env


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


def build_report(
    env: Mapping[str, str],
    *,
    require_approval_flag: bool = True,
) -> Dict[str, Any]:
    gateway_enabled = _parse_bool(env.get("AI_TRADING_SIGNAL_GATEWAY_ENABLED"))
    gateway_url = str(env.get("AI_TRADING_SIGNAL_GATEWAY_URL") or "").strip()
    token_present = bool(str(env.get("AI_TRADING_SIGNAL_GATEWAY_TOKEN") or "").strip())
    timeout_seconds = _parse_float(env.get("AI_TRADING_SIGNAL_GATEWAY_TIMEOUT_SECONDS"), 10.0)
    max_handoff_age_seconds = _parse_float(env.get("AI_TRADING_SIGNAL_MAX_HANDOFF_AGE_SECONDS"), 900.0)
    approved = _parse_bool(env.get(APPROVAL_ENV))

    blockers = []
    warnings = []
    url_parts = _sanitized_url_parts(gateway_url) if gateway_url else {
        "scheme": None,
        "host": None,
        "port": None,
        "path_present": False,
        "query_present": False,
        "credentials_embedded": False,
    }
    host = str(url_parts.get("host") or "").lower()

    if not gateway_enabled:
        blockers.append("signal_gateway_disabled")
    if not gateway_url:
        blockers.append("signal_gateway_url_missing")
    else:
        if url_parts["scheme"] != "https":
            blockers.append("signal_gateway_url_must_be_https")
        if host in LOCAL_HOSTS or _is_ip_host_private_or_local(host):
            blockers.append("signal_gateway_url_must_not_be_local_or_private")
        if host in PLACEHOLDER_HOSTS or host.endswith(".example.com"):
            blockers.append("signal_gateway_url_must_not_be_placeholder")
        if "mock" in host or "mock" in parse.urlparse(gateway_url).path.lower() or url_parts["port"] == 5621:
            blockers.append("signal_gateway_url_must_not_be_mock_gateway")
        if url_parts["credentials_embedded"] or url_parts["query_present"]:
            blockers.append("signal_gateway_url_must_not_embed_credentials_or_query")

    if not token_present:
        blockers.append("signal_gateway_token_missing")
    if timeout_seconds is None or timeout_seconds <= 0:
        blockers.append("signal_gateway_timeout_invalid")
    elif timeout_seconds > 30:
        blockers.append("signal_gateway_timeout_too_high_for_production")
    if max_handoff_age_seconds is None or max_handoff_age_seconds <= 0:
        blockers.append("signal_max_handoff_age_invalid")
    elif max_handoff_age_seconds > 900:
        blockers.append("signal_max_handoff_age_too_high_for_production")
    elif max_handoff_age_seconds > 300:
        warnings.append("signal_max_handoff_age_above_recommended_five_minutes")
    if require_approval_flag and not approved:
        blockers.append("production_handoff_approval_flag_missing")

    return {
        "production_handoff_ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "checks": {
            "gateway_enabled": gateway_enabled,
            "gateway_url": url_parts,
            "token_present": token_present,
            "token_value_returned": False,
            "timeout_seconds": timeout_seconds,
            "max_handoff_age_seconds": max_handoff_age_seconds,
            "production_handoff_approved": approved,
            "approval_env": APPROVAL_ENV,
        },
        "next_actions": [
            "Keep AI_TRADING_SIGNAL_GATEWAY_ENABLED=false until the real order backend URL/token are configured.",
            "Use an HTTPS order-backend URL that is not localhost, private-network, placeholder, or mock gateway.",
            f"Set {APPROVAL_ENV}=true only for an explicitly approved production handoff acceptance window.",
            "Run this check with --strict before any live order-backend handoff acceptance.",
        ],
    }
