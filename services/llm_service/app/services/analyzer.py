# ruff: noqa: RUF001
"""Analysis orchestrator (within llm-service).

Builds the prompt from the incoming payload, delegates to the configured provider, stores
``raw_response`` and parsed result, returns it to the caller (test-service).
"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from pkg.errors import NotFound
from pkg.logger import get_logger
from pkg.metrics import business_events
from services.llm_service.app.clients.base import LlmAnalyzer
from services.llm_service.app.models import Analysis
from services.llm_service.app.repositories.analyses import AnalysisRepository
from services.llm_service.app.schemas import AnalyzeIn

_log = get_logger("llm-service.analyzer")


def build_prompt(payload: AnalyzeIn) -> str:
    """Render the LLM prompt for free-form question grading.

    The LLM compares each user answer with the manager-provided correct answer and returns
    a per-question score on a 1..10 scale. Grading is lenient (semantic similarity, not
    literal match). Study recommendations are generated for weak topics. Response is strict JSON.
    """

    answers_by_question = {a.question_id: a for a in payload.answers}
    rendered_items: list[str] = []
    for q in payload.questions:
        ans = answers_by_question.get(q.id)
        user_answer = (ans.free_text or "").strip() if ans is not None else ""
        rendered_items.append(

                f'- question_id: "{q.id}"\n'
                f"  order: {q.order}\n"
                f"  question: {q.text}\n"
                f"  correct_answer: {q.correct_answer}\n"
                f"  user_answer: {user_answer}\n"

        )

    schema = (
        "{\n"
        '  "per_question": [ {"question_id": "<uuid>", "score": 7, '
        '"feedback": "краткое пояснение"} ],\n'
        '  "overall_score": 7.5,\n'
        '  "recommendations": [ {"topic": "...", "reason": "...", '
        '"resource_url": null} ]\n'
        "}"
    )

    return (
        f"Тест: {payload.test.title}\n"
        f"Описание: {payload.test.description or ''}\n"
        "---\n"
        f"{''.join(rendered_items)}"
        "---\n"
        "Ты — доброжелательный наставник, проверяющий знания сотрудника. "
        "По каждому вопросу сравни ответ пользователя (user_answer) с эталоном (correct_answer). "
        "Оценивай смысловую близость, а не дословное совпадение. "
        "Не будь строгим: частично верные, синонимичные и переформулированные ответы "
        "должны получать достойные баллы. "
        "Шкала оценки по каждому вопросу: от 1 до 10 (допускается один знак после запятой). "
        "Ориентиры: 9–10 — отлично, 7–8 — хорошо, 5–6 — частично верно, 3–4 — слабо, "
        "1–2 — ответ отсутствует или не по теме. "
        "overall_score — среднее арифметическое per_question.score, округлённое до одного знака. "
        "Сформируй 2–5 рекомендаций к изучению для вопросов с оценкой ниже 6: "
        "укажи тему, причину и что именно повторить (документация, инструкции, материалы). "
        "Если пользователь не ответил — поставь 1. "
        f"Верни СТРОГО валидный JSON в следующей схеме, без пояснений вне JSON: {schema}"
    )


class AnalyzerService:
    def __init__(self, *, session: AsyncSession, analyzer: LlmAnalyzer) -> None:
        self._session = session
        self._repo = AnalysisRepository(session)
        self._analyzer = analyzer

    async def analyze(self, payload: AnalyzeIn) -> Analysis:
        analysis = await self._repo.create_pending(
            attempt_id=payload.attempt_id,
            user_id=payload.user_id,
            provider=self._analyzer.name,
        )
        await self._session.commit()

        prompt = build_prompt(payload)
        try:
            result, raw = await self._analyzer.analyze(prompt, payload=payload)
        except Exception as exc:
            await self._repo.fail(analysis, error=str(exc))
            await self._session.commit()
            business_events.labels(service="llm-service", event="analyze_failed").inc()
            raise

        analysis = await self._repo.complete(
            analysis,
            prompt=prompt,
            raw_response=raw if isinstance(raw, dict) else json.loads(json.dumps(raw, default=str)),
            result=result.model_dump(),
            score=result.overall_score,
        )
        await self._session.commit()
        business_events.labels(service="llm-service", event="analyze_completed").inc()
        return analysis

    async def get(self, analysis_id) -> Analysis:
        analysis = await self._repo.get(analysis_id)
        if analysis is None:
            raise NotFound("Analysis not found")
        return analysis
