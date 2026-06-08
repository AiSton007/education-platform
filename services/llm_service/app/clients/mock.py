# ruff: noqa: RUF001
"""Deterministic mock LLM provider — used by default in dev/tests.

Grades each answer with token overlap against ``correct_answer`` and maps the result
to a 1..10 score. Produces recommendations for questions scoring below 6.
"""

from __future__ import annotations

import re

from services.llm_service.app.schemas import (
    AnalysisResult,
    AnalyzeIn,
    PerQuestionScore,
    Recommendation,
)
from services.llm_service.app.scoring import WEAK_SCORE_THRESHOLD, clamp_score

_WORD_RE = re.compile(r"[\w\-]+", re.UNICODE)


class MockAnalyzer:
    name = "mock"

    async def analyze(self, prompt: str, *, payload: AnalyzeIn) -> tuple[AnalysisResult, dict]:
        answers_by_question = {a.question_id: a for a in payload.answers}
        per_question: list[PerQuestionScore] = []
        weak_topics: list[tuple[str, float]] = []

        for q in payload.questions:
            ans = answers_by_question.get(q.id)
            user_text = (ans.free_text or "") if ans is not None else ""
            score = _grade_to_ten(user_text, q.correct_answer)
            feedback = _feedback_for(score)
            per_question.append(
                PerQuestionScore(question_id=q.id, score=score, feedback=feedback)
            )
            if score < WEAK_SCORE_THRESHOLD:
                topic_hint = q.text.strip().split("\n", 1)[0][:120]
                weak_topics.append((topic_hint, score))

        overall = (
            round(sum(p.score for p in per_question) / len(per_question), 1)
            if per_question
            else 1.0
        )

        recommendations = [
            Recommendation(
                topic=f"Повторить тему: {topic}",
                reason=(
                    f"Ответ на этот вопрос получил оценку {score:.1f} из 10. "
                    "Рекомендуется углубить знания по теме и пройти материалы повторно."
                ),
            )
            for topic, score in weak_topics[:5]
        ]

        result = AnalysisResult(
            per_question=per_question,
            overall_score=overall,
            recommendations=recommendations,
        )
        raw = {
            "provider": "mock",
            "prompt_chars": len(prompt),
            "per_question_count": len(per_question),
            "overall_score": overall,
        }
        return result, raw


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "")}


def _grade_to_ten(user_text: str, correct_answer: str) -> float:
    """Map token overlap to a lenient 1..10 score."""
    user_tokens = _tokens(user_text)
    correct_tokens = _tokens(correct_answer)
    if not user_tokens:
        return 1.0
    if not correct_tokens:
        return 5.0
    overlap = len(user_tokens & correct_tokens)
    ratio = overlap / max(1, len(correct_tokens))
    # 1 (min) .. 10 (max), lenient boost for any overlap
    raw = 1.0 + ratio * 9.0
    return clamp_score(raw)


def _feedback_for(score: float) -> str:
    if score >= 9.0:
        return "Отлично, ответ точно отражает суть вопроса."
    if score >= 7.0:
        return "Хорошо, ответ в целом соответствует ожиданиям."
    if score >= 5.0:
        return "Частично верно, но стоит углубить знания по теме."
    if score > 1.0:
        return "Слабый ответ, рекомендуется повторить материал."
    return "Ответ отсутствует или не отражает суть вопроса."
