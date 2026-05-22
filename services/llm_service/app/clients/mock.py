"""Deterministic mock LLM provider — used by default in dev/tests."""

from __future__ import annotations

from services.llm_service.app.schemas import AnalysisResult, Recommendation


class MockAnalyzer:
    name = "mock"

    async def analyze(self, prompt: str) -> tuple[AnalysisResult, dict]:
        # Trivial deterministic logic based on prompt length — good enough for happy-path tests
        # and to keep the entire MVP runnable without a real LLM.
        score = min(95.0, max(40.0, len(prompt) % 80 + 40))
        result = AnalysisResult(
            strengths=[
                "Сотрудник продемонстрировал понимание базовых концепций",
                "Структурированно подходит к ответам",
            ],
            weaknesses=[
                "Поверхностное знание процедур ИБ",
                "Слабое понимание разграничения прав доступа",
            ],
            recommendations=[
                Recommendation(
                    topic="Политика информационной безопасности",
                    resource_url="https://confluence.example/IS-policy",
                    reason="Несколько ответов содержали неточности в части обработки персональных данных.",
                ),
                Recommendation(
                    topic="RBAC и матрица доступа",
                    resource_url="https://confluence.example/RBAC",
                    reason="Требуется освежить знания по уровням доступа.",
                ),
            ],
            score=score,
        )
        raw = {"provider": "mock", "echo_prompt_chars": len(prompt), "score": score}
        return result, raw
