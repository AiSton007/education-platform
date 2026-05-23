"""Refresh-token repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.app.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: uuid.UUID, jti: str, expires_at: datetime) -> RefreshToken:
        rt = RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at)
        self._session.add(rt)
        await self._session.flush()
        return rt

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, jti: str) -> None:
        await self._session.execute(
            update(RefreshToken).where(RefreshToken.jti == jti).values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
