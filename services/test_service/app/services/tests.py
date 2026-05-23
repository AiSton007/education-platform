"""Domain service for tests (CRUD)."""

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
        _validate_questions(questions)
        test = await self._repo.create(
            title=title,
            description=description,
            created_by=created_by,
            questions=questions,
        )
        await self._session.commit()
        return test

    async def update(
        self,
        test_id: uuid.UUID,
        *,
        title: str | None,
        description: str | None,
        is_active: bool | None,
        questions: list[dict] | None,
    ) -> Test:
        test = await self._repo.get(test_id)
        if test is None:
            raise NotFound("Test not found")
        if questions is not None:
            _validate_questions(questions)
        fields: dict[str, object] = {}
        if title is not None:
            fields["title"] = title
        if description is not None:
            fields["description"] = description
        if is_active is not None:
            fields["is_active"] = is_active
        test = await self._repo.update(test, fields=fields, questions=questions)
        await self._session.commit()
        return test

    async def get(self, test_id: uuid.UUID) -> Test:
        test = await self._repo.get(test_id)
        if test is None:
            raise NotFound("Test not found")
        return test

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        active_only: bool,
    ) -> tuple[list[Test], int]:
        return await self._repo.list(limit=limit, offset=offset, active_only=active_only)

    async def delete(self, test_id: uuid.UUID) -> None:
        test = await self._repo.get(test_id)
        if test is None:
            raise NotFound("Test not found")
        await self._repo.delete(test)
        await self._session.commit()


def _validate_questions(questions: list[dict]) -> None:
    if not questions:
        raise ValidationFailed("Test must contain at least one question")
    for q in questions:
        if not q.get("text", "").strip():
            raise ValidationFailed("Question text must not be empty", details={"order": q.get("order")})
        if not q.get("correct_answer", "").strip():
            raise ValidationFailed(
                "Question must contain a non-empty correct answer",
                details={"order": q.get("order")},
            )
