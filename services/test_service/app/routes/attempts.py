"""Endpoints for attempts."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from services.test_service.app.deps import CurrentUserDep, get_attempts_service
from services.test_service.app.schemas import (
    AnswersBatch,
    AttemptOut,
    SubmitResult,
)
from services.test_service.app.services.attempts import AttemptsService

router = APIRouter(prefix="/api/v1", tags=["attempts"])

_OBSERVERS = {"manager", "admin"}


@router.post("/tests/{test_id}/start", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
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
    return SubmitResult(attempt_id=attempt.id, report_id=attempt.report_id, status=attempt.status)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
async def get_attempt(
    attempt_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[AttemptsService, Depends(get_attempts_service)],
) -> AttemptOut:
    attempt = await service.get(
        attempt_id,
        user_id=uuid.UUID(user.id),
        can_view_any=user.role in _OBSERVERS,
    )
    return AttemptOut.model_validate(attempt)
