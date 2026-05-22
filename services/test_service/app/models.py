"""SQLAlchemy models for ``test-service`` (schema ``tests``)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SCHEMA = "tests"

metadata = MetaData(schema=SCHEMA)


class Base(DeclarativeBase):
    metadata = metadata


class QuestionType(StrEnum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    FREE_TEXT = "free_text"


class AttemptStatus(StrEnum):
    STARTED = "started"
    SUBMITTED = "submitted"
    ANALYZED = "analyzed"
    COMPLETED = "completed"
    FAILED = "failed"


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="Question.order",
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", schema=SCHEMA, native_enum=True), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(6, 2), default=1.0, nullable=False)

    test: Mapped[Test] = relationship(back_populates="questions")
    options: Mapped[list["Option"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Option.order",
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question: Mapped[Question] = relationship(back_populates="options")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.tests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="attempt_status", schema=SCHEMA, native_enum=True),
        default=AttemptStatus.STARTED,
        nullable=False,
    )
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    answers: Mapped[list["Answer"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    selected_option_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    attempt: Mapped[Attempt] = relationship(back_populates="answers")
