# ruff: noqa: RUF001
"""
Проверка подключения к GigaChat API (как в документации developers.sber.ru).

Использование:
    set LLM_API_KEY=<Authorization Key>
    uv run python scripts/test_gigachat_connection.py

Опционально:
    set LLM_VERIFY_SSL=false   # если нет сертификата НУЦ Минцифры
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

OAUTH_URL = os.environ.get(
    "LLM_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
)
API_URL = os.environ.get(
    "LLM_API_URL", "https://gigachat.devices.sberbank.ru/api/v1"
).rstrip("/")
SCOPE = os.environ.get("LLM_OAUTH_SCOPE", "GIGACHAT_API_PERS")
API_KEY = os.environ.get("LLM_API_KEY", "").strip()
VERIFY_SSL = os.environ.get("LLM_VERIFY_SSL", "true").lower() in ("1", "true", "yes")


def main() -> int:
    if not API_KEY:
        print("Ошибка: задайте LLM_API_KEY (Authorization Key из кабинета developers.sber.ru)")
        return 1

    print("Шаг 1: получение Access token...")
    with httpx.Client(timeout=30.0, verify=VERIFY_SSL) as client:
        oauth_resp = client.post(
            OAUTH_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "RqUID": str(uuid.uuid4()),
                "Authorization": f"Basic {API_KEY}",
            },
            data={"scope": SCOPE},
        )
        print(f"  HTTP {oauth_resp.status_code}")
        if oauth_resp.status_code != 200:
            print(oauth_resp.text[:500])
            return 1

        token = oauth_resp.json().get("access_token")
        if not token:
            print("  В ответе нет access_token:", oauth_resp.text[:300])
            return 1
        print("  access_token получен OK")

        print("Шаг 2: GET /models (проверка Bearer)...")
        models_resp = client.get(
            f"{API_URL}/models",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        print(f"  HTTP {models_resp.status_code}")
        if models_resp.status_code != 200:
            print(models_resp.text[:500])
            return 1

        data = models_resp.json()
        models = data.get("data") or data.get("models") or []
        if isinstance(models, list) and models:
            print(f"  Доступно моделей: {len(models)}")
            for m in models[:5]:
                mid = m.get("id") or m.get("id_") or m
                print(f"    - {mid}")
        else:
            print("  Ответ:", str(data)[:400])

    print("\nGigaChat API доступен. Можно ставить LLM_PROVIDER=gigachat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
