"""Smoke test for prompt construction in llm-service."""

from __future__ import annotations

import uuid

from services.llm_service.app.schemas import (
    AnalyzeIn,
    AnswerPayload,
    QuestionPayload,
    TestPayload,
)
from services.llm_service.app.services.analyzer import build_prompt


def test_build_prompt_includes_correct_answer_and_user_answer() -> None:
    qid = "11111111-1111-1111-1111-111111111111"
    payload = AnalyzeIn(
        attempt_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        test=TestPayload(id="t1", title="ИБ-минимум", description="Базовые знания ИБ"),
        questions=[
            QuestionPayload(
                id=qid,
                order=0,
                text="Что такое 2FA?",
                correct_answer="Второй фактор аутентификации, дополняющий пароль.",
                weight=1.0,
            )
        ],
        answers=[AnswerPayload(question_id=qid, free_text="Двухфакторная аутентификация")],
    )
    prompt = build_prompt(payload)
    assert "ИБ-минимум" in prompt
    assert "Что такое 2FA?" in prompt
    assert "Второй фактор" in prompt
    assert "Двухфакторная аутентификация" in prompt
    assert '"per_question"' in prompt
    assert '"overall_score"' in prompt
    assert '"recommendations"' in prompt
    assert "1 до 10" in prompt or "1–10" in prompt
