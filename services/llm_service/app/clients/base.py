"""LLM provider abstraction.

Implementations live in sibling modules and are selected by ``LLM_PROVIDER`` env var.
The analyzer receives both the rendered ``prompt`` (already includes per-question data)
and the structured ``payload`` so deterministic backends (mock) can derive scores
without parsing the prompt.
"""

from __future__ import annotations

from typing import Protocol

from services.llm_service.app.schemas import AnalysisResult, AnalyzeIn


class LlmAnalyzer(Protocol):
    """Provider-agnostic interface that produces an :class:`AnalysisResult`."""

    name: str

    async def analyze(self, prompt: str, *, payload: AnalyzeIn) -> tuple[AnalysisResult, dict]:
        """Return ``(parsed_result, raw_response)`` for the supplied attempt payload."""
        ...
