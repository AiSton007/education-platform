"""Endpoints for analysis (internal-only)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from services.llm_service.app.deps import InternalCallerDep, get_analyzer_service
from services.llm_service.app.schemas import AnalysisResult, AnalyzeIn, AnalyzeOut
from services.llm_service.app.services.analyzer import AnalyzerService

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeOut)
async def analyze(
    payload: AnalyzeIn,
    _: InternalCallerDep,
    service: Annotated[AnalyzerService, Depends(get_analyzer_service)],
) -> AnalyzeOut:
    analysis = await service.analyze(payload)
    return _serialize(analysis)


@router.get("/analyze/{analysis_id}", response_model=AnalyzeOut)
async def get_analysis(
    analysis_id: uuid.UUID,
    _: InternalCallerDep,
    service: Annotated[AnalyzerService, Depends(get_analyzer_service)],
) -> AnalyzeOut:
    analysis = await service.get(analysis_id)
    return _serialize(analysis)


def _serialize(analysis) -> AnalyzeOut:
    return AnalyzeOut(
        id=analysis.id,
        attempt_id=analysis.attempt_id,
        user_id=analysis.user_id,
        status=analysis.status,
        score=float(analysis.score) if analysis.score is not None else None,
        result=AnalysisResult.model_validate(analysis.result) if analysis.result else None,
        provider=analysis.provider,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )
