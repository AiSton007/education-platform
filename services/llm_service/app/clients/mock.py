"""Deterministic mock LLM provider — used by default in dev/tests.

Until the real GigaChat connection is wired in, this provider grades each user answer with
a simple Jaccard-like word overlap against the manager-provided ``correct_answer``.
It always returns a 0.1-step score in [0.0, 1.0] and produces lightweight recommendations
for any question scoring below 0.7.
"""

from __future__ import annotations

import re

from services.llm_service.app.schemas import (
    AnalysisResult,
    AnalyzeIn,
    PerQuestionScore,
    Recommendation,
)

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
            score = _grade(user_text, q.correct_answer)
            feedback = _feedback_for(score)
            per_question.append(
                PerQuestionScore(question_id=q.id, score=score, feedback=feedback)
            )
            if score < 0.7:
                topic_hint = q.text.strip().split("\n", 1)[0][:120]
                weak_topics.append((topic_hint, score))

        overall = (
            round(sum(p.score for p in per_question) / len(per_question), 1)
            if per_question
            else 0.0
        )

        recommendations = [
            Recommendation(
                topic=f"Повторить тему: {topic}",
                reason=(
                    f"Ответ на этот вопрос получил низкую оценку ({score:.1f}). "
                    "Рекомендуется освежить материал и попробовать снова."
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


def _grade(user_text: str, correct_answer: str) -> float:
    """Return a score in 0.0..1.0 with 0.1 precision based on token overlap.

    The mock is intentionally lenient: a single matched non-trivial token already produces
    a partial credit, and a fully empty answer scores 0.0.
    """

    user_tokens = _tokens(user_text)
    correct_tokens = _tokens(correct_answer)
    if not user_tokens:
        return 0.0
    if not correct_tokens:
        return 0.5
    overlap = len(user_tokens & correct_tokens)
    base = overlap / max(1, len(correct_tokens))
    score = max(0.0, min(1.0, base))
    return round(score * 10) / 10


def _feedback_for(score: float) -> str:
    if score >= 0.9:
        return "Отлично, ответ точно соответствует ожиданиям."
    if score >= 0.7:
        return "Хорошо, ответ во многом совпадает с правильным."
    if score >= 0.4:
        return "Частично верно, но не хватает деталей."
    if score > 0.0:
        return "Слабый ответ, рекомендуется повторить тему."
    return "Ответ отсутствует или не отражает суть."
