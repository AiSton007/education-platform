"""Pydantic DTOs for ``test-service``."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from services.test_service.app.models import AttemptStatus, QuestionType


# ----- tests -----

class OptionIn(BaseModel):
    order: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=2000)
    is_correct: bool = False


class QuestionIn(BaseModel):
    order: int = Field(ge=0)
    type: QuestionType
    text: str = Field(min_length=1)
    weight: float = Field(default=1.0, ge=0, le=100)
    options: list[OptionIn] = Field(default_factory=list)


class TestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    questions: list[QuestionIn] = Field(default_factory=list)


class OptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order: int
    text: str
    # ``is_correct`` намеренно НЕ возвращается на /tests/{id} для employee'ев — это решается на уровне роутера.


class OptionAdminOut(OptionOut):
    is_correct: bool


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order: int
    type: QuestionType
    text: str
    weight: float
    options: list[OptionOut]


class QuestionAdminOut(QuestionOut):
    options: list[OptionAdminOut]


class TestSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    is_active: bool
    created_at: datetime


class TestOut(TestSummaryOut):
    questions: list[QuestionOut]


class TestAdminOut(TestSummaryOut):
    questions: list[QuestionAdminOut]


class TestsList(BaseModel):
    items: list[TestSummaryOut]
    total: int


# ----- attempts -----

class AnswerIn(BaseModel):
    question_id: uuid.UUID
    selected_option_ids: list[uuid.UUID] | None = None
    free_text: str | None = None


class AnswersBatch(BaseModel):
    answers: list[AnswerIn]


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    test_id: uuid.UUID
    user_id: uuid.UUID
    status: AttemptStatus
    score: float | None
    report_id: uuid.UUID | None
    analysis_id: uuid.UUID | None
    error: str | None
    started_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None


class SubmitResult(BaseModel):
    attempt_id: uuid.UUID
    report_id: uuid.UUID | None
    status: AttemptStatus
