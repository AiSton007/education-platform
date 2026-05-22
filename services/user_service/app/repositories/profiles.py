"""Async repository for user profiles."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service.app.models import Profile, Role


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        return await self._session.get(Profile, user_id)

    async def get_by_email(self, email: str) -> Profile | None:
        stmt = select(Profile).where(Profile.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int, offset: int) -> tuple[list[Profile], int]:
        items_stmt = select(Profile).order_by(Profile.created_at.desc()).limit(limit).offset(offset)
        total_stmt = select(func.count()).select_from(Profile)
        items = (await self._session.execute(items_stmt)).scalars().all()
        total = (await self._session.execute(total_stmt)).scalar_one()
        return list(items), int(total)

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        full_name: str,
        department: str | None,
        position: str | None,
        role: Role,
    ) -> Profile:
        profile = Profile(
            user_id=user_id,
            email=email.lower(),
            full_name=full_name,
            department=department,
            position=position,
            role=role,
        )
        self._session.add(profile)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile

    async def update(self, profile: Profile, *, fields: dict[str, Any]) -> Profile:
        for key, value in fields.items():
            setattr(profile, key, value)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile
