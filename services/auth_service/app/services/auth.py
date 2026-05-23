"""Authentication domain logic.

Contains all business rules: password hashing, user registration (with peer call to
user-service), login, refresh, and identity look-up.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import Conflict, NotFound, Unauthorized
from pkg.jwt_auth import decode_token, issue_access_token, issue_refresh_token
from pkg.logger import get_logger
from pkg.metrics import business_events
from services.auth_service.app.clients.user_service import UserServiceClient
from services.auth_service.app.config import AuthServiceSettings
from services.auth_service.app.models import User, UserRole
from services.auth_service.app.repositories.refresh_tokens import RefreshTokenRepository
from services.auth_service.app.repositories.users import UserRepository

_log = get_logger("auth-service.service")


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: AuthServiceSettings,
        user_service_client: UserServiceClient,
    ) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._refresh = RefreshTokenRepository(session)
        self._user_client = user_service_client

    # ----------- public api -----------

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        department: str | None,
        position: str | None,
        role: UserRole,
    ) -> User:
        existing = await self._users.get_by_email(email)
        if existing:
            raise Conflict("User with this email already exists")

        password_hash = _hash_password(password, rounds=self._settings.bcrypt_rounds)
        user = await self._users.create(email=email, password_hash=password_hash, role=role)

        try:
            await self._user_client.create_profile(
                user_id=user.id,
                email=email,
                full_name=full_name,
                department=department,
                position=position,
                role=role.value,
            )
        except Exception:
            await self._session.rollback()
            _log.exception("user_service_profile_create_failed", user_id=str(user.id))
            raise

        await self._session.commit()
        business_events.labels(service="auth-service", event="user_registered").inc()
        return user

    async def login(self, *, email: str, password: str) -> tuple[User, str, str, int, int]:
        user = await self._users.get_by_email(email)
        if not user or not _verify_password(password, user.password_hash):
            raise Unauthorized("Invalid email or password")
        return await self._issue_pair(user)

    async def refresh(self, *, refresh_token: str) -> tuple[User, str, str, int, int]:
        payload = decode_token(self._settings, refresh_token, expected_type="refresh")
        jti = str(payload["jti"])
        stored = await self._refresh.get_by_jti(jti)
        if stored is None or stored.revoked_at is not None:
            raise Unauthorized("Refresh token is not active")
        if stored.expires_at <= datetime.now(UTC):
            raise Unauthorized("Refresh token expired")

        user = await self._users.get_by_id(uuid.UUID(str(payload["sub"])))
        if user is None:
            raise Unauthorized("User no longer exists")

        await self._refresh.revoke(jti)
        pair = await self._issue_pair(user)
        await self._session.commit()
        return pair

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFound("User not found")
        return user

    # ----------- internals -----------

    async def _issue_pair(self, user: User) -> tuple[User, str, str, int, int]:
        access = issue_access_token(
            self._settings, user_id=str(user.id), role=user.role.value, email=user.email
        )
        refresh, jti = issue_refresh_token(self._settings, user_id=str(user.id))
        expires_at = datetime.fromtimestamp(
            datetime.now(UTC).timestamp() + self._settings.jwt_refresh_token_ttl,
            tz=UTC,
        )
        await self._refresh.create(user_id=user.id, jti=jti, expires_at=expires_at)
        return (
            user,
            access,
            refresh,
            self._settings.jwt_access_token_ttl,
            self._settings.jwt_refresh_token_ttl,
        )


def _hash_password(password: str, *, rounds: int) -> str:
    """Hash password with bcrypt directly (stable across passlib/bcrypt compatibility quirks)."""
    rounds = max(4, min(rounds, 31))
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Corrupted hash format should fail closed.
        return False
