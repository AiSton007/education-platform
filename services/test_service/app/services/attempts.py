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
from services.test_service.app.clients.user_service import UserServiceClient
from services.test_service.app.models import Attempt, AttemptStatus, Question, Test
from services.test_service.app.repositories.assignments import AssignmentRepository
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
        user_client: UserServiceClient,
    ) -> None:
        self._session = session
        self._tests = TestRepository(session)
        self._attempts = AttemptRepository(session)
        self._assignments = AssignmentRepository(session)
        self._llm = llm_client
        self._report = report_client
        self._users = user_client

    # ----- start / answers -----

    async def start(self, *, test_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
        test = await self._tests.get(test_id)
        if test is None:
            raise NotFound("Test not found")
        if not test.is_active:
            raise ValidationFailed("Test is not active")
        attempt = await self._attempts.create(test_id=test_id, user_id=user_id)
        await self._assignments.mark_in_progress(test_id=test_id, user_id=user_id)
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

        test = await self._tests.get(attempt.test_id)
        if test is None:
            raise NotFound("Underlying test not found")

        attempt = await self._attempts.mark_status(attempt, status=AttemptStatus.SUBMITTED)
        await self._session.commit()
        business_events.labels(service="test-service", event="attempt_submitted").inc()

        with business_latency.labels(service="test-service", event="submit_flow").time():
            try:
                analysis = await self._call_llm(test, attempt)
                result_data = analysis.get("result") or {}
                per_question = result_data.get("per_question", []) or []
                overall_score = _coerce_score(
                    result_data.get("overall_score", analysis.get("score", 1.0))
                )

                await self._attempts.update_answer_scores(attempt.id, per_question)
                attempt = await self._attempts.mark_status(
                    attempt,
                    status=AttemptStatus.ANALYZED,
                    analysis_id=uuid.UUID(str(analysis["analysis_id"])),
                    score=overall_score,
                )
                await self._session.commit()

                profile = await self._safe_fetch_profile(attempt.user_id)
                attempt = await self._attempts.get(attempt.id, with_answers=True)
                report = await self._call_report(
                    test=test,
                    attempt=attempt,
                    analysis=analysis,
                    overall_score=overall_score,
                    per_question=per_question,
                    recommendations=result_data.get("recommendations", []) or [],
                    profile=profile,
                )
                attempt = await self._attempts.mark_status(
                    attempt,
                    status=AttemptStatus.COMPLETED,
                    report_id=uuid.UUID(str(report["id"])),
                )
                await self._assignments.mark_completed(test_id=test.id, user_id=user_id)
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

    async def list_attempts(
        self,
        *,
        user_id: uuid.UUID | None,
        test_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Attempt], int]:
        return await self._attempts.list_attempts(
            user_id=user_id, test_id=test_id, limit=limit, offset=offset
        )

    async def history_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Attempt, Test]], int]:
        return await self._attempts.history_for_user(user_id, limit=limit, offset=offset)

    # ----- internals -----

    async def _safe_fetch_profile(self, user_id: uuid.UUID) -> dict:
        try:
            return await self._users.get_profile(user_id)
        except Exception:
            _log.warning("user_profile_lookup_failed", user_id=str(user_id))
            return {"user_id": str(user_id)}

    async def _call_llm(self, test: Test, attempt: Attempt) -> dict:
        answers_by_question = {str(a.question_id): a for a in attempt.answers}
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
                    "question_id": str(q.id),
                    "free_text": (
                        answers_by_question[str(q.id)].free_text
                        if str(q.id) in answers_by_question
                        else None
                    ),
                }
                for q in test.questions
            ],
        }
        return await self._llm.analyze(payload)

    async def _call_report(
        self,
        *,
        test: Test,
        attempt: Attempt,
        analysis: dict,
        overall_score: float,
        per_question: list[dict],
        recommendations: list[dict],
        profile: dict,
    ) -> dict:
        per_question_by_id = {str(p["question_id"]): p for p in per_question if "question_id" in p}
        answers_by_question = {str(a.question_id): a for a in attempt.answers}
        items: list[dict] = []
        for q in test.questions:
            qid = str(q.id)
            ans = answers_by_question.get(qid)
            pq = per_question_by_id.get(qid, {})
            items.append(
                {
                    "question_id": qid,
                    "order": q.order,
                    "text": q.text,
                    "correct_answer": q.correct_answer,
                    "user_answer": ans.free_text if ans is not None else None,
                    "score": _coerce_score(pq.get("score", 1.0)),
                    "feedback": pq.get("feedback"),
                }
            )

        payload = {
            "attempt_id": str(attempt.id),
            "user_id": str(attempt.user_id),
            "analysis_id": analysis["analysis_id"],
            "score": overall_score,
            "test": {
                "id": str(test.id),
                "title": test.title,
                "description": test.description,
            },
            "participant": {
                "user_id": str(attempt.user_id),
                "email": profile.get("email"),
                "full_name": profile.get("full_name"),
                "department": profile.get("department"),
                "position": profile.get("position"),
            },
            "items": items,
            "recommendations": recommendations,
        }
        return await self._report.create_report(payload)


def _question_payload(q: Question) -> dict:
    return {
        "id": str(q.id),
        "order": q.order,
        "text": q.text,
        "correct_answer": q.correct_answer,
        "weight": float(q.weight),
    }


def _coerce_score(value: object) -> float:
    """Clamp the score to [1.0, 10.0] and round to one decimal."""
    try:
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1.0
    score = max(1.0, min(10.0, score))
    return round(score, 1)
