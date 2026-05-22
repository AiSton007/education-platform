"""Endpoints for tests."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from pkg.errors import Forbidden
from services.test_service.app.deps import CurrentUserDep, get_tests_service
from services.test_service.app.schemas import (
    OptionOut,
    QuestionOut,
    TestAdminOut,
    TestCreate,
    TestOut,
    TestsList,
    TestSummaryOut,
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
    return TestAdminOut.model_validate(test)


@router.get("", response_model=TestsList)
async def list_tests(
    _: CurrentUserDep,
    service: Annotated[TestsService, Depends(get_tests_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TestsList:
    items, total = await service.list(limit=limit, offset=offset)
    return TestsList(
        items=[TestSummaryOut.model_validate(t) for t in items],
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
        return TestAdminOut.model_validate(test)
    # Employees should not see ``is_correct``.
    return TestOut(
        id=test.id,
        title=test.title,
        description=test.description,
        is_active=test.is_active,
        created_at=test.created_at,
        questions=[
            QuestionOut(
                id=q.id,
                order=q.order,
                type=q.type,
                text=q.text,
                weight=float(q.weight),
                options=[OptionOut(id=o.id, order=o.order, text=o.text) for o in q.options],
            )
            for q in test.questions
        ],
    )
