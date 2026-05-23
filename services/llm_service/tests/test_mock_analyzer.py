"""Smoke tests for the mock LLM provider."""

from __future__ import annotations

import uuid

import pytest

from services.llm_service.app.clients.mock import MockAnalyzer
from services.llm_service.app.schemas import (
    AnalyzeIn,
    AnswerPayload,
    QuestionPayload,
    TestPayload,
)


def _make_payload(*pairs: tuple[str, str, str]) -> AnalyzeIn:
    """Build an AnalyzeIn from (question_text, correct_answer, user_text) tuples."""
    questions = []
    answers = []
    for idx, (qtext, correct, user) in enumerate(pairs):
        qid = str(uuid.uuid4())
        questions.append(
            QuestionPayload(id=qid, order=idx, text=qtext, correct_answer=correct, weight=1.0)
        )
        answers.append(AnswerPayload(question_id=qid, free_text=user))
    return AnalyzeIn(
        attempt_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        test=TestPayload(id="t", title="Test"),
        questions=questions,
        answers=answers,
    )


@pytest.mark.asyncio
async def test_mock_returns_per_question_scores_in_range() -> None:
    payload = _make_payload(
        ("Что такое CIA?", "Confidentiality Integrity Availability", "confidentiality integrity availability"),
        ("Что такое 2FA?", "second authentication factor", ""),
    )
    analyzer = MockAnalyzer()
    result, raw = await analyzer.analyze("any prompt", payload=payload)

    assert raw["provider"] == "mock"
    assert len(result.per_question) == 2
    for score in result.per_question:
        assert 0.0 <= score.score <= 1.0
        rounded = round(score.score * 10) / 10
        assert score.score == rounded, "scores must be in 0.1 steps"

    perfect = result.per_question[0].score
    empty = result.per_question[1].score
    assert perfect > empty
    assert empty == 0.0
    assert 0.0 <= result.overall_score <= 1.0


@pytest.mark.asyncio
async def test_mock_emits_recommendations_for_weak_answers() -> None:
    payload = _make_payload(
        ("Назовите принципы ИБ", "Confidentiality Integrity Availability", "что-то совсем не то"),
    )
    result, _ = await MockAnalyzer().analyze("prompt", payload=payload)
    assert len(result.recommendations) >= 1
    assert "Повторить" in result.recommendations[0].topic
