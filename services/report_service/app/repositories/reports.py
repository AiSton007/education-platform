"""Repository for reports."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.report_service.app.models import Recommendation, Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        attempt_id: uuid.UUID,
        user_id: uuid.UUID,
        analysis_id: uuid.UUID,
        score: float,
        data: dict,
        recommendations: list[dict],
    ) -> Report:
        report = Report(
            attempt_id=attempt_id,
            user_id=user_id,
            analysis_id=analysis_id,
            score=score,
            data=data,
        )
        for r in recommendations:
            report.recommendations.append(
                Recommendation(topic=r["topic"], resource_url=r.get("resource_url"), reason=r["reason"])
            )
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report, attribute_names=["recommendations"])
        return report

    async def get(self, report_id: uuid.UUID) -> Report | None:
        stmt = select(Report).where(Report.id == report_id).options(selectinload(Report.recommendations))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID, *, limit: int, offset: int) -> tuple[list[Report], int]:
        items_stmt = (
            select(Report)
            .where(Report.user_id == user_id)
            .options(selectinload(Report.recommendations))
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count()).select_from(Report).where(Report.user_id == user_id)
        items = (await self._session.execute(items_stmt)).scalars().all()
        total = (await self._session.execute(total_stmt)).scalar_one()
        return list(items), int(total)
