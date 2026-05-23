"""Pydantic DTOs for ``test-service``.

The platform now supports only free-form questions. Multiple-choice schemas are
intentionally removed. ``correct_answer`` is exposed to managers/admins only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from services.test_service.app.models import AssignmentStatus, AttemptStatus, QuestionType

# ----- tests -----


class QuestionIn(BaseModel):
    order: int = Field(ge=0)
    text: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    weight: float = Field(default=1.0, ge=0, le=100)


class TestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    questions: list[QuestionIn] = Field(default_factory=list)


class TestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    questions: list[QuestionIn] | None = None


class QuestionOut(BaseModel):
    """Question without ``correct_answer`` — what employees see while taking a test."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order: int
    type: QuestionType
    text: str
    weight: float


class QuestionAdminOut(QuestionOut):
    """Same as :class:`QuestionOut` plus the ``correct_answer`` for managers/admins."""

    correct_answer: str


class TestSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    is_active: bool
    created_at: datetime
    questions_count: int = 0


class TestOut(TestSummaryOut):
    questions: list[QuestionOut]


class TestAdminOut(TestSummaryOut):
    questions: list[QuestionAdminOut]


class TestsList(BaseModel):
    items: list[TestSummaryOut]
    total: int


# ----- attempts / answers -----


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    free_text: str | None = None


class AnswersBatch(BaseModel):
    answers: list[AnswerIn]


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    question_id: uuid.UUID
    free_text: str | None
    score: float | None
    feedback: str | None


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


class AttemptDetailOut(AttemptOut):
    """Detail view including per-question answers; used in history & manager dashboards."""

    answers: list[AnswerOut] = Field(default_factory=list)


class AttemptsList(BaseModel):
    items: list[AttemptOut]
    total: int


class SubmitResult(BaseModel):
    attempt_id: uuid.UUID
    report_id: uuid.UUID | None
    status: AttemptStatus
    score: float | None


# ----- assignments -----


class AssignmentCreate(BaseModel):
    test_id: uuid.UUID
    user_ids: list[uuid.UUID] = Field(min_length=1)
    due_date: datetime | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    test_id: uuid.UUID
    user_id: uuid.UUID
    status: AssignmentStatus
    due_date: datetime | None
    assigned_at: datetime
    completed_at: datetime | None


class AvailableTestOut(BaseModel):
    """A test currently assigned to the employee that hasn't been finished yet."""

    model_config = ConfigDict(from_attributes=True)
    assignment_id: uuid.UUID
    test_id: uuid.UUID
    title: str
    description: str | None
    due_date: datetime | None
    questions_count: int


class AvailableTestsList(BaseModel):
    items: list[AvailableTestOut]


class AttemptHistoryItem(BaseModel):
    """An item displayed in the employee's history of passed tests."""

    model_config = ConfigDict(from_attributes=True)
    attempt_id: uuid.UUID
    test_id: uuid.UUID
    test_title: str
    status: AttemptStatus
    score: float | None
    completed_at: datetime | None
    started_at: datetime
    report_id: uuid.UUID | None


class AttemptHistoryList(BaseModel):
    items: list[AttemptHistoryItem]
    total: int
