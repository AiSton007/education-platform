"""Repository for test assignments."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from services.test_service.app.models import Assignment, AssignmentStatus, Question, Test


class AssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_assign(
        self,
        *,
        test_id: uuid.UUID,
        user_ids: list[uuid.UUID],
        assigned_by: uuid.UUID,
        due_date: datetime | None,
    ) -> list[Assignment]:
        if not user_ids:
            return []
        rows = [
            {
                "id": uuid.uuid4(),
                "test_id": test_id,
                "user_id": uid,
                "assigned_by": assigned_by,
                "status": AssignmentStatus.ASSIGNED.value,
                "due_date": due_date,
            }
            for uid in user_ids
        ]
        stmt = (
            pg_insert(Assignment)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_assignments_test_user")
        )
        await self._session.execute(stmt)
        await self._session.flush()
        ids_stmt = (
            select(Assignment)
            .where(Assignment.test_id == test_id, Assignment.user_id.in_(user_ids))
        )
        items = (await self._session.execute(ids_stmt)).scalars().all()
        return list(items)

    async def list_for_user(self, user_id: uuid.UUID) -> list[tuple[Assignment, Test, int]]:
        questions_count_subquery = (
            select(func.count())
            .select_from(Question)
            .where(Question.test_id == Test.id)
            .scalar_subquery()
        )
        stmt = (
            select(Assignment, Test, questions_count_subquery.label("questions_count"))
            .join(Test, Test.id == Assignment.test_id)
            .where(
                Assignment.user_id == user_id,
                Assignment.status != AssignmentStatus.COMPLETED,
                Test.is_active.is_(True),
            )
            .order_by(Assignment.due_date.asc().nullslast(), Assignment.assigned_at.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], row[1], int(row[2] or 0)) for row in rows]

    async def list_for_test(self, test_id: uuid.UUID) -> list[Assignment]:
        stmt = select(Assignment).where(Assignment.test_id == test_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_in_progress(self, *, test_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = select(Assignment).where(
            Assignment.test_id == test_id,
            Assignment.user_id == user_id,
        )
        item = (await self._session.execute(stmt)).scalar_one_or_none()
        if item is None or item.status == AssignmentStatus.COMPLETED:
            return
        if item.status == AssignmentStatus.ASSIGNED:
            item.status = AssignmentStatus.IN_PROGRESS
            await self._session.flush()

    async def mark_completed(self, *, test_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = select(Assignment).where(
            Assignment.test_id == test_id,
            Assignment.user_id == user_id,
        )
        item = (await self._session.execute(stmt)).scalar_one_or_none()
        if item is None:
            return
        item.status = AssignmentStatus.COMPLETED
        item.completed_at = datetime.now(UTC)
        await self._session.flush()

    async def delete(self, assignment_id: uuid.UUID) -> None:
        item = await self._session.get(Assignment, assignment_id)
        if item is not None:
            await self._session.delete(item)
            await self._session.flush()

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Assignment)
            .where(
                Assignment.user_id == user_id,
                Assignment.status != AssignmentStatus.COMPLETED,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())


__all__ = ["AssignmentRepository", "AssignmentStatus"]
