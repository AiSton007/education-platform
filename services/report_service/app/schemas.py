"""Pydantic DTOs for ``report-service``.

The new free-form business model puts the full per-question detail into the report
payload so PDF/HTML rendering can show question text, correct answer, user answer,
LLM score and feedback without any cross-service calls at render time.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MIN_SCORE = 1.0
MAX_SCORE = 10.0


class TestSummaryIn(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None


class ParticipantIn(BaseModel):
    user_id: uuid.UUID
    email: str | None = None
    full_name: str | None = None
    department: str | None = None
    position: str | None = None


class ReportItemIn(BaseModel):
    question_id: uuid.UUID
    order: int = 0
    text: str
    correct_answer: str
    user_answer: str | None = None
    score: float = Field(ge=MIN_SCORE, le=MAX_SCORE, default=MIN_SCORE)
    feedback: str | None = None


class RecommendationIn(BaseModel):
    topic: str
    reason: str
    resource_url: str | None = None


class ReportIn(BaseModel):
    """Payload accepted from test-service via internal JWT."""

    attempt_id: uuid.UUID
    user_id: uuid.UUID
    analysis_id: uuid.UUID
    score: float = Field(ge=MIN_SCORE, le=MAX_SCORE, default=MIN_SCORE)
    test: TestSummaryIn
    participant: ParticipantIn
    items: list[ReportItemIn] = Field(default_factory=list)
    recommendations: list[RecommendationIn] = Field(default_factory=list)


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
