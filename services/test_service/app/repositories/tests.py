"""Repository for tests/questions/options."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.test_service.app.models import Option, Question, Test


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
            question = Question(
                order=q["order"],
                type=q["type"],
                text=q["text"],
                weight=q["weight"],
            )
            for o in q.get("options", []):
                question.options.append(
                    Option(order=o["order"], text=o["text"], is_correct=o["is_correct"])
                )
            test.questions.append(question)
        self._session.add(test)
        await self._session.flush()
        await self._session.refresh(test, attribute_names=["questions"])
        return test

    async def get(self, test_id: uuid.UUID, *, with_options: bool = True) -> Test | None:
        stmt = (
            select(Test)
            .where(Test.id == test_id)
            .options(
                selectinload(Test.questions).selectinload(Question.options)
                if with_options
                else selectinload(Test.questions)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int, offset: int) -> tuple[list[Test], int]:
        items_stmt = (
            select(Test)
            .where(Test.is_active.is_(True))
            .order_by(Test.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count()).select_from(Test).where(Test.is_active.is_(True))
        items = (await self._session.execute(items_stmt)).scalars().all()
        total = (await self._session.execute(total_stmt)).scalar_one()
        return list(items), int(total)
