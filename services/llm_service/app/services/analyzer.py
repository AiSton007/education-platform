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
    """Render the LLM prompt.

    Strict JSON schema: ``{strengths:[], weaknesses:[], recommendations:[{topic, resource_url, reason}], score: 0-100}``.
    """
    questions_map = {q.id: q for q in payload.questions}
    rendered_qa = []
    for ans in payload.answers:
        q = questions_map.get(ans.question_id)
        if q is None:
            continue
        if q.type in ("single", "multiple") and ans.selected_option_ids:
            selected_texts = [
                o.text for o in q.options if o.id in ans.selected_option_ids
            ]
            correct_texts = [o.text for o in q.options if o.is_correct]
            rendered_qa.append(
                f"Вопрос: {q.text}\nВыбрано: {selected_texts}\nПравильно: {correct_texts}\n"
            )
        else:
            rendered_qa.append(f"Вопрос: {q.text}\nОтвет (текст): {ans.free_text or ''}\n")

    schema = (
        '{"strengths":["..."],"weaknesses":["..."],'
        '"recommendations":[{"topic":"...","resource_url":"...","reason":"..."}],'
        '"score":0}'
    )
    return (
        f"Тест: {payload.test.title}\n"
        f"Описание: {payload.test.description or ''}\n"
        f"---\n"
        f"{''.join(rendered_qa)}\n---\n"
        f"Проанализируй ответы сотрудника, выдели сильные и слабые стороны, "
        f"предложи материалы для изучения (включай ссылки на Confluence и инструкции, "
        f"если уверен) и поставь общую оценку от 0 до 100. "
        f"Ответ верни строго в JSON следующего формата без какого-либо текста до или после: {schema}"
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
            result, raw = await self._analyzer.analyze(prompt)
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
            score=result.score,
        )
        await self._session.commit()
        business_events.labels(service="llm-service", event="analyze_completed").inc()
        return analysis

    async def get(self, analysis_id) -> Analysis:
        analysis = await self._repo.get(analysis_id)
        if analysis is None:
            raise NotFound("Analysis not found")
        return analysis
