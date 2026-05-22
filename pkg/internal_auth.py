"""Service-to-service JWT.

Distinct from the user-facing JWT: uses ``INTERNAL_JWT_SECRET`` and asserts
``iss in allowed_callers`` and ``aud == self_service_name``. Tokens are short-lived (TTL 5 min
by default) and issued just-in-time by the calling service.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Header

from pkg.config import InternalJWTSettings
from pkg.errors import Forbidden, Unauthorized

INTERNAL_TOKEN_HEADER = "X-Internal-Token"


@dataclass(frozen=True)
class InternalCaller:
    """Identity of the calling microservice."""

    issuer: str


class InternalIssuer:
    """Mint short-lived service tokens.

    Example::

        issuer = InternalIssuer(self_name="test-service", settings=settings)
        token = issuer.token(audience="llm-service")
    """

    def __init__(self, self_name: str, settings: InternalJWTSettings) -> None:
        self._self = self_name
        self._settings = settings

    def token(self, audience: str) -> str:
        now = int(time.time())
        payload = {
            "iss": self._self,
            "aud": audience,
            "iat": now,
            "exp": now + self._settings.internal_jwt_ttl,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(
            payload,
            self._settings.internal_jwt_secret,
            algorithm=self._settings.internal_jwt_algorithm,
        )


def _decode_internal(settings: InternalJWTSettings, audience: str, token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.internal_jwt_secret,
            algorithms=[settings.internal_jwt_algorithm],
            audience=audience,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Internal token expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise Forbidden("Internal token aud mismatch") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("Invalid internal token") from exc


def make_internal_caller_dep(settings: InternalJWTSettings, audience: str, *allowed: str):
    """Build a FastAPI dependency requiring a valid internal token from ``allowed`` issuers.

    ``audience`` should be the service's own name (e.g. ``"llm-service"``).
    """

    allowed_set = set(allowed)

    async def _dep(
        token: Annotated[str | None, Header(alias=INTERNAL_TOKEN_HEADER)] = None,
    ) -> InternalCaller:
        if not token:
            raise Unauthorized(f"Missing {INTERNAL_TOKEN_HEADER} header")
        payload = _decode_internal(settings, audience, token)
        iss = str(payload.get("iss", ""))
        if iss not in allowed_set:
            raise Forbidden(f"Issuer '{iss}' is not in allow-list")
        return InternalCaller(issuer=iss)

    return _dep


def make_user_or_internal_dep(
    settings: InternalJWTSettings,
    audience: str,
    *allowed: str,
    user_dep,
):
    """Dependency that accepts either a valid user JWT or a valid internal token.

    Useful for read-only debug endpoints exposed via the gateway but also called by another
    service internally.
    """

    allowed_set = set(allowed)

    async def _dep(
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        internal_token: Annotated[str | None, Header(alias=INTERNAL_TOKEN_HEADER)] = None,
    ):
        if internal_token:
            payload = _decode_internal(settings, audience, internal_token)
            iss = str(payload.get("iss", ""))
            if iss not in allowed_set:
                raise Forbidden(f"Issuer '{iss}' is not in allow-list")
            return InternalCaller(issuer=iss)
        return await user_dep(authorization=authorization)

    return _dep
