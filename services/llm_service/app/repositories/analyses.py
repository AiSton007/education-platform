"""Repository for analyses."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from services.llm_service.app.models import Analysis, AnalysisStatus


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(self, *, attempt_id: uuid.UUID, user_id: uuid.UUID, provider: str) -> Analysis:
        analysis = Analysis(
            attempt_id=attempt_id,
            user_id=user_id,
            provider=provider,
            status=AnalysisStatus.PROCESSING,
        )
        self._session.add(analysis)
        await self._session.flush()
        await self._session.refresh(analysis)
        return analysis

    async def get(self, analysis_id: uuid.UUID) -> Analysis | None:
        return await self._session.get(Analysis, analysis_id)

    async def complete(
        self,
        analysis: Analysis,
        *,
        prompt: str,
        raw_response: dict,
        result: dict,
        score: float,
    ) -> Analysis:
        analysis.prompt = prompt
        analysis.raw_response = raw_response
        analysis.result = result
        analysis.score = score
        analysis.status = AnalysisStatus.COMPLETED
        await self._session.flush()
        await self._session.refresh(analysis)
        return analysis

    async def fail(self, analysis: Analysis, *, error: str) -> Analysis:
        analysis.status = AnalysisStatus.FAILED
        analysis.error = error[:1000]
        await self._session.flush()
        await self._session.refresh(analysis)
        return analysis
