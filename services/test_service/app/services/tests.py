"""Domain service for tests (CRUD-ish)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import NotFound, ValidationFailed
from services.test_service.app.models import Test
from services.test_service.app.repositories.tests import TestRepository


class TestsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TestRepository(session)

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        created_by: uuid.UUID,
        questions: list[dict],
    ) -> Test:
        if not questions:
            raise ValidationFailed("Test must contain at least one question")
        for q in questions:
            if q["type"] in ("single", "multiple") and len(q.get("options", [])) < 2:
                raise ValidationFailed(
                    "Multiple-choice question must contain at least 2 options",
                    details={"question_order": q.get("order")},
                )
        test = await self._repo.create(
            title=title,
            description=description,
            created_by=created_by,
            questions=questions,
        )
        await self._session.commit()
        return test

    async def get(self, test_id: uuid.UUID) -> Test:
        test = await self._repo.get(test_id, with_options=True)
        if test is None:
            raise NotFound("Test not found")
        return test

    async def list(self, *, limit: int, offset: int) -> tuple[list[Test], int]:
        return await self._repo.list(limit=limit, offset=offset)
