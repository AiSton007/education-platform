"""Orchestrator for the submit-flow.

This is the **only** place that talks to llm-service and report-service. Other services never
initiate cross-service calls — they only receive payloads.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import Forbidden, NotFound, ValidationFailed
from pkg.logger import get_logger
from pkg.metrics import business_events, business_latency
from services.test_service.app.clients.llm_service import LlmServiceClient
from services.test_service.app.clients.report_service import ReportServiceClient
from services.test_service.app.models import Attempt, AttemptStatus, Question, QuestionType, Test
from services.test_service.app.repositories.attempts import AttemptRepository
from services.test_service.app.repositories.tests import TestRepository

_log = get_logger("test-service.attempts")


class AttemptsService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        llm_client: LlmServiceClient,
        report_client: ReportServiceClient,
    ) -> None:
        self._session = session
        self._tests = TestRepository(session)
        self._attempts = AttemptRepository(session)
        self._llm = llm_client
        self._report = report_client

    # ----- start / answers -----

    async def start(self, *, test_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
        test = await self._tests.get(test_id, with_options=True)
        if test is None:
            raise NotFound("Test not found")
        if not test.is_active:
            raise ValidationFailed("Test is not active")
        attempt = await self._attempts.create(test_id=test_id, user_id=user_id)
        await self._session.commit()
        business_events.labels(service="test-service", event="attempt_started").inc()
        return attempt

    async def submit_answers(
        self,
        *,
        attempt_id: uuid.UUID,
        user_id: uuid.UUID,
        answers: list[dict],
    ) -> Attempt:
        attempt = await self._attempts.get(attempt_id, with_answers=False)
        if attempt is None:
            raise NotFound("Attempt not found")
        if attempt.user_id != user_id:
            raise Forbidden("Cannot answer foreign attempt")
        if attempt.status != AttemptStatus.STARTED:
            raise ValidationFailed("Attempt is no longer accepting answers")
        await self._attempts.upsert_answers(attempt_id, answers)
        await self._session.commit()
        return attempt

    # ----- submit (orchestrator) -----

    async def submit(self, *, attempt_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
        attempt = await self._attempts.get(attempt_id, with_answers=True)
        if attempt is None:
            raise NotFound("Attempt not found")
        if attempt.user_id != user_id:
            raise Forbidden("Cannot submit foreign attempt")
        if attempt.status not in (AttemptStatus.STARTED, AttemptStatus.SUBMITTED):
            raise ValidationFailed(f"Attempt cannot be submitted from status '{attempt.status.value}'")

        test = await self._tests.get(attempt.test_id, with_options=True)
        if test is None:
            raise NotFound("Underlying test not found")

        attempt = await self._attempts.mark_status(attempt, status=AttemptStatus.SUBMITTED)
        await self._session.commit()
        business_events.labels(service="test-service", event="attempt_submitted").inc()

        with business_latency.labels(service="test-service", event="submit_flow").time():
            try:
                analysis = await self._call_llm(test, attempt)
                attempt = await self._attempts.mark_status(
                    attempt,
                    status=AttemptStatus.ANALYZED,
                    analysis_id=uuid.UUID(str(analysis["analysis_id"])),
                    score=float(analysis.get("score", 0.0)),
                )
                await self._session.commit()

                report = await self._call_report(attempt, analysis)
                attempt = await self._attempts.mark_status(
                    attempt,
                    status=AttemptStatus.COMPLETED,
                    report_id=uuid.UUID(str(report["id"])),
                )
                await self._session.commit()
                business_events.labels(service="test-service", event="attempt_completed").inc()
            except Exception as exc:
                _log.exception("submit_flow_failed", attempt_id=str(attempt_id))
                attempt = await self._attempts.mark_status(
                    attempt, status=AttemptStatus.FAILED, error=str(exc)[:1000]
                )
                await self._session.commit()
                business_events.labels(service="test-service", event="attempt_failed").inc()
                raise

        return attempt

    async def get(self, attempt_id: uuid.UUID, *, user_id: uuid.UUID, can_view_any: bool) -> Attempt:
        attempt = await self._attempts.get(attempt_id, with_answers=True)
        if attempt is None:
            raise NotFound("Attempt not found")
        if not can_view_any and attempt.user_id != user_id:
            raise Forbidden("Cannot view foreign attempt")
        return attempt

    # ----- internals -----

    async def _call_llm(self, test: Test, attempt: Attempt) -> dict:
        payload = {
            "attempt_id": str(attempt.id),
            "user_id": str(attempt.user_id),
            "test": {
                "id": str(test.id),
                "title": test.title,
                "description": test.description,
            },
            "questions": [_question_payload(q) for q in test.questions],
            "answers": [
                {
                    "question_id": str(a.question_id),
                    "selected_option_ids": [str(x) for x in (a.selected_option_ids or [])],
                    "free_text": a.free_text,
                }
                for a in attempt.answers
            ],
        }
        return await self._llm.analyze(payload)

    async def _call_report(self, attempt: Attempt, analysis: dict) -> dict:
        payload = {
            "attempt_id": str(attempt.id),
            "user_id": str(attempt.user_id),
            "analysis_id": analysis["analysis_id"],
            "analysis": analysis.get("result", {}),
            "score": float(analysis.get("score", 0.0)),
        }
        return await self._report.create_report(payload)


def _question_payload(q: Question) -> dict:
    base = {
        "id": str(q.id),
        "order": q.order,
        "type": q.type.value,
        "text": q.text,
        "weight": float(q.weight),
    }
    if q.type in (QuestionType.SINGLE, QuestionType.MULTIPLE):
        base["options"] = [
            {"id": str(o.id), "order": o.order, "text": o.text, "is_correct": o.is_correct} for o in q.options
        ]
    return base
