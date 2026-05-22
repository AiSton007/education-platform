"""Smoke test for prompt construction in llm-service."""

from __future__ import annotations

import uuid

from services.llm_service.app.schemas import (
    AnalyzeIn,
    AnswerPayload,
    OptionPayload,
    QuestionPayload,
    TestPayload,
)
from services.llm_service.app.services.analyzer import build_prompt


def test_build_prompt_renders_test_and_answers() -> None:
    qid = "11111111-1111-1111-1111-111111111111"
    payload = AnalyzeIn(
        attempt_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        test=TestPayload(id="t1", title="ИБ-минимум", description="Базовые знания ИБ"),
        questions=[
            QuestionPayload(
                id=qid,
                order=0,
                type="single",
                text="Что такое 2FA?",
                weight=1.0,
                options=[
                    OptionPayload(id="o1", order=0, text="Двойной пароль", is_correct=False),
                    OptionPayload(id="o2", order=1, text="Второй фактор аутентификации", is_correct=True),
                ],
            )
        ],
        answers=[AnswerPayload(question_id=qid, selected_option_ids=["o2"])],
    )
    prompt = build_prompt(payload)
    assert "ИБ-минимум" in prompt
    assert "Что такое 2FA?" in prompt
    assert '"strengths"' in prompt
    assert "score" in prompt
