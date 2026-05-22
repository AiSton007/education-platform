"""User-facing JWT issuance and validation.

The same module is used by ``auth-service`` (issuer + validator) and by all other backend
services (validator only).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header

from pkg.config import JWTSettings
from pkg.errors import Forbidden, Unauthorized


@dataclass(frozen=True)
class CurrentUser:
    """Identity attached to an authenticated request."""

    id: str
    role: str
    email: str | None = None


def issue_access_token(settings: JWTSettings, *, user_id: str, role: str, email: str | None = None) -> str:
    now = int(time.time())
    payload: dict[str, object] = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + settings.jwt_access_token_ttl,
        "iss": settings.jwt_issuer,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def issue_refresh_token(settings: JWTSettings, *, user_id: str) -> tuple[str, str]:
    """Return ``(token, jti)``. The ``jti`` is stored server-side to allow revocation."""
    now = int(time.time())
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + settings.jwt_refresh_token_ttl,
        "iss": settings.jwt_issuer,
        "type": "refresh",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(settings: JWTSettings, token: str, *, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("Invalid token") from exc
    if expected_type and payload.get("type") != expected_type:
        raise Unauthorized(f"Expected token type '{expected_type}'")
    return payload


def make_current_user_dep(settings: JWTSettings):
    """Build a FastAPI dependency that resolves ``CurrentUser`` from ``Authorization``."""

    async def _dep(
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    ) -> CurrentUser:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise Unauthorized("Missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_token(settings, token, expected_type="access")
        return CurrentUser(
            id=str(payload["sub"]),
            role=str(payload.get("role", "employee")),
            email=payload.get("email"),
        )

    return _dep


def require_roles(*allowed: str):
    """Dependency factory that ensures ``CurrentUser.role`` is one of ``allowed``."""

    def _dep(current_user_dep):
        async def _inner(user: CurrentUser = Depends(current_user_dep)) -> CurrentUser:
            if user.role not in allowed:
                raise Forbidden(f"Role '{user.role}' is not allowed")
            return user

        return _inner

    return _dep
