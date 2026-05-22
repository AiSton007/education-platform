"""Domain service for reports."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import NotFound
from pkg.metrics import business_events
from services.report_service.app.models import Report
from services.report_service.app.repositories.reports import ReportRepository


class ReportsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReportRepository(session)

    async def create(
        self,
        *,
        attempt_id: uuid.UUID,
        user_id: uuid.UUID,
        analysis_id: uuid.UUID,
        score: float,
        analysis: dict,
    ) -> Report:
        report = await self._repo.create(
            attempt_id=attempt_id,
            user_id=user_id,
            analysis_id=analysis_id,
            score=score,
            data=analysis,
            recommendations=analysis.get("recommendations", []),
        )
        await self._session.commit()
        business_events.labels(service="report-service", event="report_created").inc()
        return report

    async def get(self, report_id: uuid.UUID) -> Report:
        report = await self._repo.get(report_id)
        if report is None:
            raise NotFound("Report not found")
        return report

    async def list_by_user(self, user_id: uuid.UUID, *, limit: int, offset: int) -> tuple[list[Report], int]:
        return await self._repo.list_by_user(user_id, limit=limit, offset=offset)
