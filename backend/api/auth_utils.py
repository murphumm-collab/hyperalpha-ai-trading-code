"""
Shared API authentication helpers.

The legacy app supports local/demo mode through the `default` user. For To C
traffic, Hyper AI endpoints should resolve a concrete user from the request and
scope profile, memory, conversations, and jobs to that user.
"""

import base64
import hashlib
import json
import re
import time
from typing import Any, Dict, Optional

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


def _decode_base64url(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("utf-8"))


def _decode_bearer_payload(authorization: Optional[str]) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None

    token = authorization[len(prefix):].strip()
    parts = token.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    try:
        payload = json.loads(_decode_base64url(parts[1]).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token payload") from exc

    exp = payload.get("exp")
    if exp is not None:
        try:
            if int(exp) < int(time.time()):
                raise HTTPException(status_code=401, detail="Bearer token expired")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid bearer token expiry") from exc

    return payload


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
        return user

    return create_user(db, username=username, email=email)


def resolve_request_user(
    db: Session,
    session_token: Optional[str] = None,
    authorization: Optional[str] = None,
    allow_default: bool = True,
) -> User:
    """
    Resolve the current user for an API request.

    Production note: bearer JWT signature verification is not implemented here
    yet. This helper only decodes a trusted gateway/SSO token enough to map it
    to a local user. Add issuer + JWKS verification before accepting this as a
    production auth boundary.
    """
    if session_token:
        user_id = verify_auth_session(db, session_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Session user not found")
        return user

    bearer_payload = _decode_bearer_payload(authorization)
    if bearer_payload:
        return _user_from_bearer_payload(db, bearer_payload)

    if allow_default:
        return get_or_create_user(db, username="default")

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
