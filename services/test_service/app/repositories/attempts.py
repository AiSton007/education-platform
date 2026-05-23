"""Repository for attempts/answers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.test_service.app.models import Answer, Attempt, AttemptStatus, Test


class AttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, test_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
        attempt = Attempt(test_id=test_id, user_id=user_id, status=AttemptStatus.STARTED)
        self._session.add(attempt)
        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt

    async def get(self, attempt_id: uuid.UUID, *, with_answers: bool = False) -> Attempt | None:
        stmt = select(Attempt).where(Attempt.id == attempt_id)
        if with_answers:
            stmt = stmt.options(selectinload(Attempt.answers))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_answers(self, attempt_id: uuid.UUID, answers: list[dict]) -> None:
        question_ids = [a["question_id"] for a in answers]
        if question_ids:
            await self._session.execute(
                delete(Answer).where(Answer.attempt_id == attempt_id, Answer.question_id.in_(question_ids))
            )
        for a in answers:
            self._session.add(
                Answer(
                    attempt_id=attempt_id,
                    question_id=a["question_id"],
                    free_text=a.get("free_text"),
                )
            )
        await self._session.flush()

    async def update_answer_scores(self, attempt_id: uuid.UUID, per_question: list[dict]) -> None:
        for entry in per_question:
            stmt = (
                select(Answer)
                .where(
                    Answer.attempt_id == attempt_id,
                    Answer.question_id == uuid.UUID(str(entry["question_id"])),
                )
                .limit(1)
            )
            ans = (await self._session.execute(stmt)).scalar_one_or_none()
            if ans is None:
                continue
            score_val = entry.get("score")
            if score_val is not None:
                ans.score = float(score_val)
            feedback_val = entry.get("feedback")
            if feedback_val is not None:
                ans.feedback = str(feedback_val)
        await self._session.flush()

    async def mark_status(
        self,
        attempt: Attempt,
        *,
        status: AttemptStatus,
        score: float | None = None,
        report_id: uuid.UUID | None = None,
        analysis_id: uuid.UUID | None = None,
        error: str | None = None,
    ) -> Attempt:
        attempt.status = status
        if score is not None:
            attempt.score = score
        if report_id is not None:
            attempt.report_id = report_id
        if analysis_id is not None:
            attempt.analysis_id = analysis_id
        if error is not None:
            attempt.error = error
        if status == AttemptStatus.SUBMITTED:
            attempt.submitted_at = datetime.now(UTC)
        if status in (AttemptStatus.COMPLETED, AttemptStatus.FAILED):
            attempt.completed_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt

    async def list_attempts(
        self,
        *,
        user_id: uuid.UUID | None,
        test_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Attempt], int]:
        stmt = select(Attempt).order_by(Attempt.started_at.desc())
        total_stmt = select(func.count()).select_from(Attempt)
        if user_id is not None:
            stmt = stmt.where(Attempt.user_id == user_id)
            total_stmt = total_stmt.where(Attempt.user_id == user_id)
        if test_id is not None:
            stmt = stmt.where(Attempt.test_id == test_id)
            total_stmt = total_stmt.where(Attempt.test_id == test_id)
        items = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()
        total = (await self._session.execute(total_stmt)).scalar_one()
        return list(items), int(total)

    async def history_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Attempt, Test]], int]:
        stmt = (
            select(Attempt, Test)
            .join(Test, Test.id == Attempt.test_id)
            .where(Attempt.user_id == user_id)
            .order_by(Attempt.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id)
        rows = (await self._session.execute(stmt)).all()
        items = [(row[0], row[1]) for row in rows]
        total = (await self._session.execute(total_stmt)).scalar_one()
        return items, int(total)
