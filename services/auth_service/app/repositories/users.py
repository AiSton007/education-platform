"""User repository — thin async data-access layer over SQLAlchemy."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.app.models import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def create(self, *, email: str, password_hash: str, role: UserRole) -> User:
        user = User(email=email.lower(), password_hash=password_hash, role=role)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user
