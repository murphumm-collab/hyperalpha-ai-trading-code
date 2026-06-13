"""
Shared API authentication helpers.

The legacy app supports local/demo mode through the `default` user. For To C
traffic, Hyper AI endpoints should resolve a concrete user from the request and
scope profile, memory, conversations, and jobs to that user.
"""

import base64
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Optional

import requests
from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from repositories.user_repo import (
    create_user,
    get_or_create_user,
    get_user,
    get_user_by_username,
    update_user,
    verify_auth_session,
)


_USERNAME_SAFE_RE = re.compile(r"[^a-zA-Z0-9_-]+")
_JWKS_CACHE: Dict[str, Any] = {"url": None, "expires_at": 0, "keys": []}
_DEFAULT_AUTH_ALGORITHMS = "RS256"
_ADMIN_ROLES = {"admin", "operator"}


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _lower_csv_env(name: str, default: str = "") -> set[str]:
    return {item.lower() for item in _csv_env(name, default)}


def _claim_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value.lower()}
    if isinstance(value, (list, tuple, set)):
        return {str(item).lower() for item in value}
    return {str(value).lower()}


def _payload_has_admin_claim(payload: Optional[Dict[str, Any]]) -> bool:
    if not payload:
        return False

    if payload.get("is_admin") is True or payload.get("admin") is True:
        return True

    admin_values = _lower_csv_env("AUTH_ADMIN_CLAIM_VALUES", "admin,operator")
    claim_names = _csv_env("AUTH_ADMIN_CLAIM_NAMES", "role,roles,groups,permissions")
    for claim_name in claim_names:
        if _claim_values(payload.get(claim_name)).intersection(admin_values):
            return True
    return False


def _identity_is_env_admin(username: Optional[str], email: Optional[str]) -> bool:
    admin_usernames = _lower_csv_env("AUTH_ADMIN_USERNAMES", "default")
    admin_emails = _lower_csv_env("AUTH_ADMIN_EMAILS")

    if username and username.lower() in admin_usernames:
        return True
    if email and email.lower() in admin_emails:
        return True
    return False


def is_admin_user(user: User) -> bool:
    """Return True when a user is allowed to call system-admin endpoints."""
    role = str(getattr(user, "role", "") or "").lower()
    return role in _ADMIN_ROLES or _identity_is_env_admin(user.username, user.email)


def _sync_request_role(
    db: Session,
    user: User,
    payload: Optional[Dict[str, Any]] = None,
) -> User:
    should_be_admin = _identity_is_env_admin(user.username, user.email) or _payload_has_admin_claim(payload)
    if should_be_admin and str(getattr(user, "role", "") or "").lower() not in _ADMIN_ROLES:
        update_user(db, user.id, role="admin")
        db.refresh(user)
    elif not getattr(user, "role", None):
        update_user(db, user.id, role="user")
        db.refresh(user)
    return user


def _decode_base64url(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("utf-8"))


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None

    return authorization[len(prefix):].strip()


def _decode_jwt_segment(token: str, segment_index: int, error_detail: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) < segment_index + 1:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    try:
        decoded = json.loads(_decode_base64url(parts[segment_index]).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail=error_detail) from exc

    if not isinstance(decoded, dict):
        raise HTTPException(status_code=401, detail=error_detail)
    return decoded


def _validate_registered_claims(payload: Dict[str, Any]) -> None:
    now = int(time.time())
    leeway = int(os.getenv("AUTH_JWT_LEEWAY_SECONDS", "60"))

    exp = payload.get("exp")
    if exp is not None:
        try:
            if int(exp) < now - leeway:
                raise HTTPException(status_code=401, detail="Bearer token expired")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid bearer token expiry") from exc

    nbf = payload.get("nbf")
    if nbf is not None:
        try:
            if int(nbf) > now + leeway:
                raise HTTPException(status_code=401, detail="Bearer token not active yet")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid bearer token nbf") from exc

    expected_issuer = os.getenv("AUTH_JWT_ISSUER", "").strip()
    if expected_issuer and payload.get("iss") != expected_issuer:
        raise HTTPException(status_code=401, detail="Invalid bearer token issuer")

    expected_audiences = _csv_env("AUTH_JWT_AUDIENCE")
    if expected_audiences:
        aud = payload.get("aud")
        if isinstance(aud, str):
            token_audiences = {aud}
        elif isinstance(aud, list):
            token_audiences = {str(item) for item in aud}
        else:
            token_audiences = set()
        if not token_audiences.intersection(expected_audiences):
            raise HTTPException(status_code=401, detail="Invalid bearer token audience")


def _get_jwks_keys(jwks_url: str) -> list[Dict[str, Any]]:
    cache_seconds = int(os.getenv("AUTH_JWKS_CACHE_SECONDS", "300"))
    now = int(time.time())
    if (
        _JWKS_CACHE["url"] == jwks_url
        and int(_JWKS_CACHE["expires_at"]) > now
        and isinstance(_JWKS_CACHE["keys"], list)
    ):
        return _JWKS_CACHE["keys"]

    try:
        response = requests.get(jwks_url, timeout=10, allow_redirects=False)
        response.raise_for_status()
        jwks = response.json()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to fetch JWKS") from exc

    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise HTTPException(status_code=503, detail="Invalid JWKS response")

    _JWKS_CACHE.update({
        "url": jwks_url,
        "expires_at": now + cache_seconds,
        "keys": keys,
    })
    return keys


def _find_jwk(keys: list[Dict[str, Any]], kid: Optional[str], alg: str) -> Dict[str, Any]:
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        raise HTTPException(status_code=401, detail="Bearer token key not found")

    matching = [key for key in keys if key.get("alg") in (None, alg)]
    if len(matching) == 1:
        return matching[0]
    raise HTTPException(status_code=401, detail="Bearer token missing key id")


def _rsa_public_key_from_jwk(jwk: Dict[str, Any]):
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
    except Exception as exc:
        raise HTTPException(status_code=500, detail="JWT verification dependency unavailable") from exc

    if jwk.get("kty") != "RSA" or not jwk.get("n") or not jwk.get("e"):
        raise HTTPException(status_code=401, detail="Unsupported bearer token key")

    modulus = int.from_bytes(_decode_base64url(str(jwk["n"])), "big")
    exponent = int.from_bytes(_decode_base64url(str(jwk["e"])), "big")
    return rsa.RSAPublicNumbers(exponent, modulus).public_key()


def _verify_jwt_signature(token: str, jwk: Dict[str, Any], alg: str) -> None:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
    except Exception as exc:
        raise HTTPException(status_code=500, detail="JWT verification dependency unavailable") from exc

    hash_algorithms = {
        "RS256": hashes.SHA256(),
        "RS384": hashes.SHA384(),
        "RS512": hashes.SHA512(),
    }
    hash_algorithm = hash_algorithms.get(alg)
    if not hash_algorithm:
        raise HTTPException(status_code=401, detail="Unsupported bearer token algorithm")

    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    signature = _decode_base64url(parts[2])
    public_key = _rsa_public_key_from_jwk(jwk)

    try:
        public_key.verify(signature, signing_input, padding.PKCS1v15(), hash_algorithm)
    except InvalidSignature as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token signature") from exc


def _decode_unverified_bearer_payload(token: str) -> Dict[str, Any]:
    payload = _decode_jwt_segment(token, 1, "Invalid bearer token payload")
    _validate_registered_claims(payload)
    return payload


def _decode_verified_bearer_payload(token: str, jwks_url: str) -> Dict[str, Any]:
    header = _decode_jwt_segment(token, 0, "Invalid bearer token header")
    payload = _decode_jwt_segment(token, 1, "Invalid bearer token payload")

    alg = str(header.get("alg") or "")
    allowed_algorithms = set(_csv_env("AUTH_JWT_ALGORITHMS", _DEFAULT_AUTH_ALGORITHMS))
    if alg not in allowed_algorithms:
        raise HTTPException(status_code=401, detail="Unsupported bearer token algorithm")

    keys = _get_jwks_keys(jwks_url)
    jwk = _find_jwk(keys, header.get("kid"), alg)
    _verify_jwt_signature(token, jwk, alg)
    _validate_registered_claims(payload)
    return payload


def _decode_bearer_payload(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    token = _extract_bearer_token(authorization)
    if not token:
        return None

    jwks_url = os.getenv("AUTH_JWKS_URL", "").strip()
    if jwks_url:
        return _decode_verified_bearer_payload(token, jwks_url)

    if _truthy_env("AUTH_REQUIRE_VERIFIED_BEARER"):
        raise HTTPException(status_code=401, detail="Bearer verification is not configured")

    return _decode_unverified_bearer_payload(token)


def _user_from_bearer_payload(db: Session, payload: Dict[str, Any]) -> User:
    external_id = (
        payload.get("id")
        or payload.get("sub")
        or payload.get("owner")
        or payload.get("email")
    )
    if not external_id:
        raise HTTPException(status_code=401, detail="Bearer token missing user identity")

    email = payload.get("email")
    if isinstance(email, str):
        email = email[:100]
    else:
        email = None

    digest = hashlib.sha256(str(external_id).encode("utf-8")).hexdigest()[:24]
    username_hint = str(payload.get("name") or payload.get("displayName") or external_id)
    username_hint = _USERNAME_SAFE_RE.sub("_", username_hint).strip("_").lower()[:16]
    username = f"sso_{username_hint}_{digest}" if username_hint else f"sso_{digest}"
    username = username[:50]

    user = get_user_by_username(db, username)
    if user:
        if email and not user.email:
            update_user(db, user.id, email=email)
            db.refresh(user)
        return _sync_request_role(db, user, payload)

    role = "admin" if _payload_has_admin_claim(payload) or _identity_is_env_admin(username, email) else "user"
    return create_user(db, username=username, email=email, role=role)


def resolve_request_user(
    db: Session,
    session_token: Optional[str] = None,
    authorization: Optional[str] = None,
    allow_default: bool = True,
) -> User:
    """
    Resolve the current user for an API request.

    Production note: set AUTH_JWKS_URL to verify Bearer JWT signatures against
    a JWKS endpoint. AUTH_JWT_ISSUER, AUTH_JWT_AUDIENCE, AUTH_JWT_ALGORITHMS,
    and AUTH_REQUIRE_VERIFIED_BEARER can be used to tighten the boundary.
    """
    if session_token:
        user_id = verify_auth_session(db, session_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Session user not found")
        return _sync_request_role(db, user)

    bearer_payload = _decode_bearer_payload(authorization)
    if bearer_payload:
        return _user_from_bearer_payload(db, bearer_payload)

    if allow_default:
        user = get_or_create_user(db, username="default", role="admin")
        return _sync_request_role(db, user)

    raise HTTPException(status_code=401, detail="Authentication required")


def get_current_user_dependency(
    session_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    return resolve_request_user(
        db=db,
        session_token=session_token,
        authorization=authorization,
        allow_default=True,
    )


def get_authenticated_user_dependency(
    session_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    return resolve_request_user(
        db=db,
        session_token=session_token,
        authorization=authorization,
        allow_default=False,
    )


def get_admin_user_dependency(
    session_token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    user = resolve_request_user(
        db=db,
        session_token=session_token,
        authorization=authorization,
        allow_default=False,
    )
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
