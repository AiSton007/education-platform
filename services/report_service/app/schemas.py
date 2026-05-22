"""Pydantic DTOs for ``report-service``."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecommendationIn(BaseModel):
    topic: str
    resource_url: str | None = None
    reason: str


class AnalysisPayload(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationIn] = Field(default_factory=list)
    score: float = 0.0


class ReportIn(BaseModel):
    """Payload accepted from test-service via internal JWT."""

    attempt_id: uuid.UUID
    user_id: uuid.UUID
    analysis_id: uuid.UUID
    analysis: AnalysisPayload
    score: float = Field(ge=0, le=100, default=0.0)


class RecommendationOut(RecommendationIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_id: uuid.UUID
    user_id: uuid.UUID
    analysis_id: uuid.UUID
    score: float
    data: dict
    created_at: datetime
    recommendations: list[RecommendationOut]


class ReportsList(BaseModel):
    items: list[ReportOut]
    total: int
