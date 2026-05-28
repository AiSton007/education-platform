"""Endpoints for test assignments."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from pkg.errors import Forbidden
from services.test_service.app.deps import CurrentUserDep, get_assignments_service
from services.test_service.app.schemas import (
    AssignmentCreate,
    AssignmentOut,
    AvailableTestOut,
    AvailableTestsList,
)
from services.test_service.app.services.assignments import AssignmentsService

router = APIRouter(prefix="/api/v1", tags=["assignments"])

_AUTHORS = {"manager", "admin"}


@router.post(
    "/assignments",
    response_model=list[AssignmentOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_assignments(
    payload: AssignmentCreate,
    user: CurrentUserDep,
    service: Annotated[AssignmentsService, Depends(get_assignments_service)],
) -> list[AssignmentOut]:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can assign tests")
    items = await service.assign(
        test_id=payload.test_id,
        user_ids=payload.user_ids,
        assigned_by=uuid.UUID(user.id),
        due_date=payload.due_date,
    )
    return [AssignmentOut.model_validate(i) for i in items]


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def revoke_assignment(
    assignment_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[AssignmentsService, Depends(get_assignments_service)],
) -> Response:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can revoke assignments")
    await service.revoke(assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tests/{test_id}/assignments", response_model=list[AssignmentOut])
async def list_assignments_for_test(
    test_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[AssignmentsService, Depends(get_assignments_service)],
) -> list[AssignmentOut]:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can view assignments for a test")
    items = await service.list_for_test(test_id)
    return [AssignmentOut.model_validate(i) for i in items]


@router.get("/assignments/me", response_model=AvailableTestsList)
async def list_my_assignments(
    user: CurrentUserDep,
    service: Annotated[AssignmentsService, Depends(get_assignments_service)],
) -> AvailableTestsList:
    rows = await service.list_for_user(uuid.UUID(user.id))
    items = [
        AvailableTestOut(
            assignment_id=a.id,
            test_id=t.id,
            title=t.title,
            description=t.description,
            due_date=a.due_date,
            questions_count=questions_count,
        )
        for a, t, questions_count in rows
    ]
    return AvailableTestsList(items=items)
