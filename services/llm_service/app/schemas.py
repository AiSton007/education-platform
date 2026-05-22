"""Pydantic DTOs for ``llm-service``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from services.llm_service.app.models import AnalysisStatus


class OptionPayload(BaseModel):
    id: str
    order: int
    text: str
    is_correct: bool


class QuestionPayload(BaseModel):
    id: str
    order: int
    type: str
    text: str
    weight: float
    options: list[OptionPayload] = Field(default_factory=list)


class AnswerPayload(BaseModel):
    question_id: str
    selected_option_ids: list[str] = Field(default_factory=list)
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


class Recommendation(BaseModel):
    topic: str
    resource_url: str | None = None
    reason: str


class AnalysisResult(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    score: float = Field(ge=0, le=100)


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
