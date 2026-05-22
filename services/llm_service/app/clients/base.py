"""LLM provider abstraction.

Implementations live in sibling modules and are selected by ``LLM_PROVIDER`` env var.
"""

from __future__ import annotations

from typing import Protocol

from services.llm_service.app.schemas import AnalysisResult


class LlmAnalyzer(Protocol):
    """Provider-agnostic interface that produces an :class:`AnalysisResult`."""

    name: str

    async def analyze(self, prompt: str) -> tuple[AnalysisResult, dict]:
        """Return ``(parsed_result, raw_response)``."""
        ...
