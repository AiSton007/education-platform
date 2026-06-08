"""Shared score helpers for llm-service (scale 1..10)."""

from __future__ import annotations

MIN_SCORE = 1.0
MAX_SCORE = 10.0
WEAK_SCORE_THRESHOLD = 6.0


def clamp_score(value: object, *, default: float = MIN_SCORE) -> float:
    """Clamp to [1.0, 10.0] and round to one decimal."""
    try:
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    score = max(MIN_SCORE, min(MAX_SCORE, score))
    return round(score, 1)
