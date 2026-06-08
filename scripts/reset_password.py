# ruff: noqa: RUF001
"""
Сброс пароля пользователя (bcrypt, как в auth-service).

Способ 1 — через admin API (рекомендуется):
    uv run python scripts/reset_password.py --api \\
        --email user@example.com \\
        --password new-strong-password-123 \\
        --admin-email admin@example.com \\
        --admin-password admin-pass-12345

Способ 2 — напрямую в PostgreSQL (если нет admin-логина):
    set DB_HOST=localhost
    set DB_PORT=5432
    set DB_NAME=education
    set DB_USER=auth_user
    set DB_PASSWORD=auth_pass_change_me
    uv run python scripts/reset_password.py --db \\
        --email user@example.com \\
        --password new-strong-password-123
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

import bcrypt
import httpx
import psycopg2

DEFAULT_GW = "http://localhost:18080"
BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _login(gw: str, email: str, password: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{gw.rstrip('/')}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("login response has no access_token")
        return token


def _find_user_id(gw: str, admin_token: str, email: str) -> str:
    target = email.strip().lower()
    offset = 0
    limit = 200
    with httpx.Client(timeout=30.0) as client:
        while True:
            resp = client.get(
                f"{gw.rstrip('/')}/api/v1/users",
                params={"limit": limit, "offset": offset},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                if str(item.get("email", "")).lower() == target:
                    return str(item["user_id"])
            total = int(data.get("total", 0))
            offset += limit
            if offset >= total:
                break
    raise RuntimeError(f"user not found by email: {email}")


def reset_via_api(
    *,
    gw: str,
    email: str,
    new_password: str,
    admin_email: str,
    admin_password: str,
) -> None:
    admin_token = _login(gw, admin_email, admin_password)
    user_id = _find_user_id(gw, admin_token, email)
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{gw.rstrip('/')}/api/v1/auth/admin/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": user_id, "new_password": new_password},
        )
        if resp.status_code == 403:
            raise RuntimeError("admin account required (role=admin)")
        resp.raise_for_status()
    print(f"OK: password reset via API for {email} (user_id={user_id})")


def reset_via_db(*, email: str, new_password: str) -> None:
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "5432"))
    dbname = os.environ.get("DB_NAME", "education")
    user = os.environ.get("DB_USER") or os.environ.get("AUTH_DB_USER")
    password = os.environ.get("DB_PASSWORD") or os.environ.get("AUTH_DB_PASSWORD")
    if not user or not password:
        raise RuntimeError("set DB_USER/DB_PASSWORD or AUTH_DB_USER/AUTH_DB_PASSWORD")

    password_hash = _hash_password(new_password)
    now = datetime.now(UTC)

    with psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE auth.users
                SET password_hash = %s, updated_at = %s
                WHERE lower(email) = lower(%s)
                RETURNING id
                """,
                (password_hash, now, email),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"user not found in auth.users: {email}")
            user_id = row[0]
            cur.execute(
                """
                UPDATE auth.refresh_tokens
                SET revoked_at = %s
                WHERE user_id = %s AND revoked_at IS NULL
                """,
                (now, user_id),
            )
        conn.commit()

    print(f"OK: password reset in DB for {email} (user_id={user_id})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset user password (bcrypt)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--api", action="store_true", help="reset via admin API")
    mode.add_argument("--db", action="store_true", help="reset directly in PostgreSQL")
    parser.add_argument("--email", required=True, help="target user email (login)")
    parser.add_argument("--password", required=True, help="new password (min 8 chars)")
    parser.add_argument("--gw", default=os.environ.get("GW", DEFAULT_GW), help="api-gateway URL")
    parser.add_argument("--admin-email", help="admin login email (for --api)")
    parser.add_argument("--admin-password", help="admin login password (for --api)")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Ошибка: пароль должен быть не короче 8 символов")
        return 1

    try:
        if args.api:
            if not args.admin_email or not args.admin_password:
                print("Ошибка: для --api укажите --admin-email и --admin-password")
                return 1
            reset_via_api(
                gw=args.gw,
                email=args.email,
                new_password=args.password,
                admin_email=args.admin_email,
                admin_password=args.admin_password,
            )
        else:
            reset_via_db(email=args.email, new_password=args.password)
    except httpx.HTTPStatusError as exc:
        print(f"HTTP ошибка: {exc.response.status_code} {exc.response.text}")
        return 1
    except Exception as exc:  # noqa: BLE001 — CLI script
        print(f"Ошибка: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
