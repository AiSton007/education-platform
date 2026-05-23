"""Pydantic DTOs for ``llm-service``.

Free-form grading model: payload now carries each question's ``correct_answer`` so the
LLM (or mock provider) can compare it against the user's free-text answer and return a
per-question score in the 0.0..1.0 range (one decimal).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.llm_service.app.models import AnalysisStatus


class QuestionPayload(BaseModel):
    id: str
    order: int
    text: str
    correct_answer: str
    weight: float = 1.0


class AnswerPayload(BaseModel):
    question_id: str
    free_text: str | None = None


class TestPayload(BaseModel):
    id: str
    title: str
    description: str | None = None


class AnalyzeIn(BaseModel):
    attempt_id: uuid.UUID
    user_id: uuid.UUID
    test: TestPayload
    questions: list[QuestionPayload]
    answers: list[AnswerPayload]


class PerQuestionScore(BaseModel):
    question_id: str
    score: float = Field(ge=0.0, le=1.0)
    feedback: str | None = None

    @field_validator("score")
    @classmethod
    def _round_to_one_decimal(cls, v: float) -> float:
        return round(max(0.0, min(1.0, float(v))), 1)


class Recommendation(BaseModel):
    topic: str
    reason: str
    resource_url: str | None = None


class AnalysisResult(BaseModel):
    """Result returned by the analyzer for a single attempt."""

    per_question: list[PerQuestionScore] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    recommendations: list[Recommendation] = Field(default_factory=list)

    @field_validator("overall_score")
    @classmethod
    def _round_overall(cls, v: float) -> float:
        return round(max(0.0, min(1.0, float(v))), 1)


class AnalyzeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    analysis_id: uuid.UUID = Field(validation_alias="id")
    attempt_id: uuid.UUID
    user_id: uuid.UUID
    status: AnalysisStatus
    score: float | None = None
    result: AnalysisResult | None = None
    provider: str
    created_at: datetime
    updated_at: datetime


class AnalysisRaw(BaseModel):
    """Raw response stored alongside parsed result for auditing."""

    response: dict[str, Any]
