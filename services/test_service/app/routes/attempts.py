"""Endpoints for attempts."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from pkg.errors import Forbidden
from services.test_service.app.deps import CurrentUserDep, get_attempts_service
from services.test_service.app.models import Answer, Attempt
from services.test_service.app.schemas import (
    AnswerOut,
    AnswersBatch,
    AttemptDetailOut,
    AttemptHistoryItem,
    AttemptHistoryList,
    AttemptOut,
    AttemptsList,
    SubmitResult,
)
from services.test_service.app.services.attempts import AttemptsService

router = APIRouter(prefix="/api/v1", tags=["attempts"])

_OBSERVERS = {"manager", "admin"}


@router.post(
    "/tests/{test_id}/start", response_model=AttemptOut, status_code=status.HTTP_201_CREATED
)
async def start_attempt(
    test_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
) -> AttemptOut:
    attempt = await service.start(test_id=test_id, user_id=uuid.UUID(user.id))
    return AttemptOut.model_validate(attempt)


@router.post("/attempts/{attempt_id}/answers", response_model=AttemptOut)
async def submit_answers(
    attempt_id: uuid.UUID,
    payload: AnswersBatch,
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
) -> AttemptOut:
    attempt = await service.submit_answers(
        attempt_id=attempt_id,
        user_id=uuid.UUID(user.id),
        answers=[a.model_dump() for a in payload.answers],
    )
    return AttemptOut.model_validate(attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitResult)
async def submit_attempt(
    attempt_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
) -> SubmitResult:
    attempt = await service.submit(attempt_id=attempt_id, user_id=uuid.UUID(user.id))
    return SubmitResult(
        attempt_id=attempt.id,
        report_id=attempt.report_id,
        status=attempt.status,
        score=float(attempt.score) if attempt.score is not None else None,
    )


@router.get("/attempts/{attempt_id}", response_model=AttemptDetailOut)
async def get_attempt(
    attempt_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
) -> AttemptDetailOut:
    attempt = await service.get(
        attempt_id,
        user_id=uuid.UUID(user.id),
        can_view_any=user.role in _OBSERVERS,
    )
    return _serialize_detail(attempt)


@router.get("/attempts", response_model=AttemptsList)
async def list_attempts(
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: uuid.UUID | None = Query(default=None),
    test_id: uuid.UUID | None = Query(default=None),
) -> AttemptsList:
    if user.role not in _OBSERVERS:
        raise Forbidden("Only managers and admins can list attempts")
    items, total = await service.list_attempts(
        user_id=user_id, test_id=test_id, limit=limit, offset=offset
    )
    return AttemptsList(items=[AttemptOut.model_validate(a) for a in items], total=total)


@router.get("/attempts/me/history", response_model=AttemptHistoryList)
async def my_history(
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AttemptHistoryList:
    rows, total = await service.history_for_user(
        uuid.UUID(user.id), limit=limit, offset=offset
    )
    items = [
        AttemptHistoryItem(
            attempt_id=a.id,
            test_id=a.test_id,
            test_title=t.title,
            status=a.status,
            score=float(a.score) if a.score is not None else None,
            completed_at=a.completed_at,
            started_at=a.started_at,
            report_id=a.report_id,
        )
        for a, t in rows
    ]
    return AttemptHistoryList(items=items, total=total)


def _serialize_detail(attempt: Attempt) -> AttemptDetailOut:
    return AttemptDetailOut(
        id=attempt.id,
        test_id=attempt.test_id,
        user_id=attempt.user_id,
        status=attempt.status,
        score=float(attempt.score) if attempt.score is not None else None,
        report_id=attempt.report_id,
        analysis_id=attempt.analysis_id,
        error=attempt.error,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        completed_at=attempt.completed_at,
        answers=[_answer_out(a) for a in attempt.answers],
    )


def _answer_out(a: Answer) -> AnswerOut:
    return AnswerOut(
        id=a.id,
        question_id=a.question_id,
        free_text=a.free_text,
        score=float(a.score) if a.score is not None else None,
        feedback=a.feedback,
    )
