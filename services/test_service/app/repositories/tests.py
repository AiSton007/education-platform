"""Repository for tests/questions (free-form only)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.test_service.app.models import Question, QuestionType, Test


class TestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        created_by: uuid.UUID,
        questions: list[dict],
    ) -> Test:
        test = Test(title=title, description=description, created_by=created_by)
        for q in questions:
            test.questions.append(_build_question(q))
        self._session.add(test)
        await self._session.flush()
        await self._session.refresh(test, attribute_names=["questions"])
        return test

    async def update(
        self,
        test: Test,
        *,
        fields: dict[str, Any],
        questions: list[dict] | None,
    ) -> Test:
        for key, value in fields.items():
            setattr(test, key, value)
        if questions is not None:
            await self._session.execute(delete(Question).where(Question.test_id == test.id))
            test.questions = [_build_question(q) for q in questions]
        await self._session.flush()
        await self._session.refresh(test, attribute_names=["questions"])
        return test

    async def get(self, test_id: uuid.UUID) -> Test | None:
        stmt = (
            select(Test)
            .where(Test.id == test_id)
            .options(selectinload(Test.questions))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        active_only: bool,
    ) -> tuple[list[Test], int]:
        stmt = select(Test).options(selectinload(Test.questions)).order_by(Test.created_at.desc())
        total_stmt = select(func.count()).select_from(Test)
        if active_only:
            stmt = stmt.where(Test.is_active.is_(True))
            total_stmt = total_stmt.where(Test.is_active.is_(True))
        items = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()
        total = (await self._session.execute(total_stmt)).scalar_one()
        return list(items), int(total)

    async def delete(self, test: Test) -> None:
        await self._session.delete(test)
        await self._session.flush()


def _build_question(q: dict) -> Question:
    return Question(
        order=q["order"],
        type=QuestionType.FREE_TEXT,
        text=q["text"],
        correct_answer=q["correct_answer"],
        weight=q.get("weight", 1.0),
    )
