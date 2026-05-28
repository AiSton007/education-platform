"""Endpoints for tests (free-form only)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from pkg.errors import Forbidden
from services.test_service.app.deps import CurrentUserDep, get_tests_service
from services.test_service.app.models import Test
from services.test_service.app.schemas import (
    QuestionAdminOut,
    QuestionOut,
    TestAdminOut,
    TestCreate,
    TestOut,
    TestsList,
    TestSummaryOut,
    TestUpdate,
)
from services.test_service.app.services.tests import TestsService

router = APIRouter(prefix="/api/v1/tests", tags=["tests"])

_AUTHORS = {"manager", "admin"}


@router.post("", response_model=TestAdminOut, status_code=status.HTTP_201_CREATED)
async def create_test(
    payload: TestCreate,
    user: CurrentUserDep,
    service: Annotated[TestsService, Depends(get_tests_service)],
) -> TestAdminOut:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can create tests")
    test = await service.create(
        title=payload.title,
        description=payload.description,
        created_by=uuid.UUID(user.id),
        questions=[q.model_dump() for q in payload.questions],
    )
    return _serialize_admin(test)


@router.patch("/{test_id}", response_model=TestAdminOut)
async def update_test(
    test_id: uuid.UUID,
    payload: TestUpdate,
    user: CurrentUserDep,
    service: Annotated[TestsService, Depends(get_tests_service)],
) -> TestAdminOut:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can update tests")
    test = await service.update(
        test_id,
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
        questions=[q.model_dump() for q in payload.questions] if payload.questions is not None else None,
    )
    return _serialize_admin(test)


@router.delete(
    "/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_test(
    test_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[TestsService, Depends(get_tests_service)],
) -> Response:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can delete tests")
    await service.delete(test_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=TestsList)
async def list_tests(
    user: CurrentUserDep,
    service: Annotated[TestsService, Depends(get_tests_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    active_only: bool | None = Query(default=None),
) -> TestsList:
    effective_active_only = active_only if active_only is not None else user.role not in _AUTHORS
    items, total = await service.list(limit=limit, offset=offset, active_only=effective_active_only)
    return TestsList(
        items=[_serialize_summary(t) for t in items],
        total=total,
    )


@router.get("/{test_id}", response_model=TestOut)
async def get_test(
    test_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[TestsService, Depends(get_tests_service)],
):
    test = await service.get(test_id)
    if user.role in _AUTHORS:
        return _serialize_admin(test)
    return _serialize_employee(test)


def _serialize_summary(test: Test) -> TestSummaryOut:
    return TestSummaryOut(
        id=test.id,
        title=test.title,
        description=test.description,
        is_active=test.is_active,
        created_at=test.created_at,
        questions_count=len(test.questions),
    )


def _serialize_employee(test: Test) -> TestOut:
    return TestOut(
        id=test.id,
        title=test.title,
        description=test.description,
        is_active=test.is_active,
        created_at=test.created_at,
        questions_count=len(test.questions),
        questions=[
            QuestionOut(
                id=q.id,
                order=q.order,
                type=q.type,
                text=q.text,
                weight=float(q.weight),
            )
            for q in test.questions
        ],
    )


def _serialize_admin(test: Test) -> TestAdminOut:
    return TestAdminOut(
        id=test.id,
        title=test.title,
        description=test.description,
        is_active=test.is_active,
        created_at=test.created_at,
        questions_count=len(test.questions),
        questions=[
            QuestionAdminOut(
                id=q.id,
                order=q.order,
                type=q.type,
                text=q.text,
                weight=float(q.weight),
                correct_answer=q.correct_answer,
            )
            for q in test.questions
        ],
    )
