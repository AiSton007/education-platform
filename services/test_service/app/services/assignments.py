"""Assignments domain service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import NotFound
from services.test_service.app.models import Assignment, Test
from services.test_service.app.repositories.assignments import AssignmentRepository
from services.test_service.app.repositories.tests import TestRepository


class AssignmentsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AssignmentRepository(session)
        self._tests = TestRepository(session)

    async def assign(
        self,
        *,
        test_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        assigned_by: uuid.UUID,
        due_date: datetime | None,
    ) -> list[Assignment]:
        test = await self._tests.get(test_id)
        if test is None:
            raise NotFound("Test not found")
        created = await self._repo.bulk_assign(
            test_id=test_id,
            user_ids=user_ids,
            assigned_by=assigned_by,
            due_date=due_date,
        )
        await self._session.commit()
        return created

    async def list_for_test(self, test_id: uuid.UUID) -> list[Assignment]:
        return await self._repo.list_for_test(test_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[tuple[Assignment, Test]]:
        return await self._repo.list_for_user(user_id)

    async def revoke(self, assignment_id: uuid.UUID) -> None:
        await self._repo.delete(assignment_id)
        await self._session.commit()
