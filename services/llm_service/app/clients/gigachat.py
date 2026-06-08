# ruff: noqa: RUF001
"""GigaChat LLM provider (REST API, same flow as developers.sber.ru docs).

1. POST ``LLM_OAUTH_URL`` — ``Authorization: Basic <Authorization Key>``,
   ``scope=GIGACHAT_API_PERS``, header ``RqUID`` → ``access_token`` (≈30 min).
2. POST ``{LLM_API_URL}/chat/completions`` — ``Authorization: Bearer <token>``,
   prompt → JSON with per-question scores 1..10 and recommendations.

``LLM_API_KEY`` = Authorization Key from the Sber developer cabinet (not Client ID).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx

from pkg.errors import UpstreamError
from pkg.logger import get_logger
from services.llm_service.app.config import LlmServiceSettings
from services.llm_service.app.scoring import MIN_SCORE, clamp_score
from services.llm_service.app.schemas import (
    AnalysisResult,
    AnalyzeIn,
    PerQuestionScore,
    Recommendation,
)

_log = get_logger("llm-service.gigachat")


class GigaChatAnalyzer:
    name = "gigachat"

    def __init__(self, settings: LlmServiceSettings) -> None:
        if not settings.llm_api_key.strip():
            raise ValueError(
                "LLM_API_KEY is required when LLM_PROVIDER=gigachat "
                "(Authorization Key from developers.sber.ru)"
            )
        self._settings = settings
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._client = httpx.AsyncClient(
            timeout=settings.llm_timeout_seconds, verify=settings.llm_verify_ssl
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        rq_uid = str(uuid.uuid4())
        headers = {
            "Authorization": f"Basic {self._settings.llm_api_key}",
            "RqUID": rq_uid,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        data = {"scope": self._settings.llm_oauth_scope}
        try:
            response = await self._client.post(self._settings.llm_oauth_url, headers=headers, data=data)
        except httpx.RequestError as exc:
            raise UpstreamError("GigaChat OAuth request failed", details={"err": str(exc)}) from exc

        if response.status_code != 200:
            raise UpstreamError(
                "GigaChat OAuth returned non-200",
                details={"status": response.status_code, "body": response.text[:500]},
            )
        payload = response.json()
        self._token = str(payload["access_token"])
        if "expires_at" in payload:
            self._token_expires_at = float(payload["expires_at"]) / 1000
        else:
            self._token_expires_at = time.time() + float(payload.get("expires_in", 1800))
        return self._token

    async def analyze(self, prompt: str, *, payload: AnalyzeIn) -> tuple[AnalysisResult, dict]:
        token = await self._ensure_token()
        body = {
            "model": self._settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты наставник, проверяющий ответы сотрудников на корпоративные тесты. "
                        "Оценивай смысловую близость, не дословное совпадение. "
                        "Шкала: 1–10 баллов за вопрос. Не будь строгим. "
                        "Отвечай ТОЛЬКО валидным JSON без markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            response = await self._client.post(
                f"{self._settings.llm_api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
            )
        except httpx.RequestError as exc:
            raise UpstreamError("GigaChat completion request failed", details={"err": str(exc)}) from exc

        if response.status_code != 200:
            raise UpstreamError(
                "GigaChat completion returned non-200",
                details={"status": response.status_code, "body": response.text[:500]},
            )
        raw = response.json()
        text = _extract_message(raw)
        try:
            parsed: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UpstreamError(
                "Failed to parse GigaChat response as JSON",
                details={"snippet": text[:500]},
            ) from exc
        result = _to_analysis_result(parsed, payload)
        return result, raw


def _extract_message(raw: dict[str, Any]) -> str:
    try:
        return str(raw["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise UpstreamError("GigaChat response has unexpected shape") from exc


def _to_analysis_result(parsed: dict[str, Any], payload: AnalyzeIn) -> AnalysisResult:
    known_question_ids = {q.id for q in payload.questions}
    per_question_raw = parsed.get("per_question", []) or []
    per_question: list[PerQuestionScore] = []
    for item in per_question_raw:
        qid = str(item.get("question_id", ""))
        if qid not in known_question_ids:
            continue
        per_question.append(
            PerQuestionScore(
                question_id=qid,
                score=clamp_score(item.get("score", MIN_SCORE)),
                feedback=item.get("feedback"),
            )
        )

    # Fallback: ensure every question has a score (minimum 1 if the model skipped it).
    scored_ids = {p.question_id for p in per_question}
    for q in payload.questions:
        if q.id not in scored_ids:
            per_question.append(PerQuestionScore(question_id=q.id, score=MIN_SCORE))

    overall = parsed.get("overall_score")
    if overall is None and per_question:
        overall = round(sum(p.score for p in per_question) / len(per_question), 1)
    elif overall is None:
        overall = MIN_SCORE
    overall = clamp_score(overall)

    recommendations = [
        Recommendation(
            topic=str(r.get("topic", "")),
            reason=str(r.get("reason", "")),
            resource_url=r.get("resource_url"),
        )
        for r in parsed.get("recommendations", []) or []
        if r.get("topic")
    ]

    return AnalysisResult(
        per_question=per_question,
        overall_score=float(overall),
        recommendations=recommendations,
    )
