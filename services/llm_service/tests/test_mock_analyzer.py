"""Smoke test for the mock LLM provider."""

from __future__ import annotations

import pytest

from services.llm_service.app.clients.mock import MockAnalyzer


@pytest.mark.asyncio
async def test_mock_returns_structured_result() -> None:
    analyzer = MockAnalyzer()
    result, raw = await analyzer.analyze("Some prompt for the mock analyzer")
    assert 0 <= result.score <= 100
    assert result.strengths
    assert result.weaknesses
    assert result.recommendations
    assert raw["provider"] == "mock"
