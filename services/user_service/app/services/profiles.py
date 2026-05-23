"""Profile domain service."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import Conflict, NotFound
from services.user_service.app.models import Profile, Role
from services.user_service.app.repositories.profiles import ProfileRepository


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProfileRepository(session)

    async def get(self, user_id: uuid.UUID) -> Profile:
        profile = await self._repo.get(user_id)
        if profile is None:
            raise NotFound("Profile not found")
        return profile

    async def list(self, *, limit: int, offset: int) -> tuple[list[Profile], int]:
        return await self._repo.list(limit=limit, offset=offset)

    async def create_internal(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        full_name: str,
        department: str | None,
        position: str | None,
        role: Role,
    ) -> Profile:
        existing = await self._repo.get(user_id)
        if existing is not None:
            raise Conflict("Profile already exists")
        try:
            profile = await self._repo.create(
                user_id=user_id,
                email=email,
                full_name=full_name,
                department=department,
                position=position,
                role=role,
            )
        except IntegrityError as exc:
            await self._session.rollback()
            raise Conflict("Profile already exists") from exc
        await self._session.commit()
        return profile

    async def patch(self, user_id: uuid.UUID, *, fields: dict[str, object]) -> Profile:
        profile = await self.get(user_id)
        clean = {k: v for k, v in fields.items() if v is not None}
        if not clean:
            return profile
        profile = await self._repo.update(profile, fields=clean)
        await self._session.commit()
        return profile

    async def deactivate(self, user_id: uuid.UUID) -> Profile:
        profile = await self.get(user_id)
        profile = await self._repo.update(profile, fields={"is_active": False})
        await self._session.commit()
        return profile
