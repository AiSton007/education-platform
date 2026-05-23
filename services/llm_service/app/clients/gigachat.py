"""GigaChat LLM provider.

Implements the two-step flow:

1. POST to ``LLM_OAUTH_URL`` with ``Authorization: Basic <client_id:client_secret>`` and
   ``scope=GIGACHAT_API_PERS`` body to obtain a short-lived access token.
2. POST ``/chat/completions`` to ``LLM_API_URL`` with ``Authorization: Bearer <token>`` and a
   prompt that instructs the model to return strict JSON (per-question scores 0.0..1.0
   plus recommendations).

The response is parsed as JSON (best effort) and mapped to :class:`AnalysisResult`.
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
                        "Ты помощник аналитики результатов тестирования сотрудников. "
                        "Сравнивай свободные ответы пользователей с правильными ответами по смыслу. "
                        "Будь мягким, но честным. Отвечай ТОЛЬКО валидным JSON в указанной схеме."
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
                score=float(item.get("score", 0.0)),
                feedback=item.get("feedback"),
            )
        )

    # Fallback: ensure every question has a score (default 0.0 if the model skipped it).
    scored_ids = {p.question_id for p in per_question}
    for q in payload.questions:
        if q.id not in scored_ids:
            per_question.append(PerQuestionScore(question_id=q.id, score=0.0))

    overall = parsed.get("overall_score")
    if overall is None and per_question:
        overall = round(sum(p.score for p in per_question) / len(per_question), 1)
    elif overall is None:
        overall = 0.0

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
