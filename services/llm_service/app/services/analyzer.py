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

    The LLM is asked to compare each user's answer with the manager-provided correct answer
    and to return a per-question score in the 0.0..1.0 range (with 0.1 precision). It is
    explicitly instructed to be lenient and to grade by semantic similarity, not literal
    string match. After scoring, it must produce concise study recommendations for the
    weakest topics. The schema is strict JSON so the response can be parsed safely.
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
        '  "per_question": [ {"question_id": "<uuid>", "score": 0.0, '
        '"feedback": "краткое пояснение"} ],\n'
        '  "overall_score": 0.0,\n'
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
        "Ты — мягкий, но честный экзаменатор. По каждому вопросу сравни ответ пользователя "
        "(user_answer) с правильным ответом (correct_answer). Оценивай смысловую близость, "
        "а не буквальное совпадение. Не будь чрезмерно строгим: частично верные, синонимичные "
        "и переформулированные ответы должны получать высокие оценки. "
        "Оценка по каждому вопросу — число от 0.0 до 1.0 с шагом 0.1 (0.0, 0.1, ..., 1.0). "
        "Подсчитай overall_score как среднее арифметическое per_question.score, округлённое "
        "до одного знака после запятой. "
        "Сформируй краткие рекомендации к изучению на основе тем тех вопросов, где пользователь "
        "получил низкую оценку (score < 0.7). Рекомендации должны быть понятными и опираться "
        "на конкретную слабость пользователя. "
        "Если пользователь не ответил — поставь 0.0. "
        f"Верни СТРОГО валидный JSON в следующей схеме, без пояснений: {schema}"
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
