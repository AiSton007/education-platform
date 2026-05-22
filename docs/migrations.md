# Миграции (Alembic)

У каждого сервиса свой Alembic с собственной таблицей `alembic_version` внутри его схемы.

## Локально

```bash
# Применить миграции одного сервиса (внутри docker-compose):
docker compose --profile migrate run --rm auth-migrate

# Запустить весь набор миграций разом:
docker compose --profile migrate up --abort-on-container-exit
```

Без Docker (нужны переменные окружения сервиса):

```bash
uv run alembic -c services/auth_service/alembic.ini upgrade head
uv run alembic -c services/auth_service/alembic.ini downgrade -1
```

## Создание новой миграции

```bash
# 1. Поправить services/<svc>/app/models.py
# 2. Сгенерировать ревизию (autogenerate):
uv run alembic -c services/auth_service/alembic.ini revision \
  --autogenerate -m "add field X"
# 3. Проверить файл в services/<svc>/alembic/versions/, при необходимости поправить.
# 4. Применить:
uv run alembic -c services/auth_service/alembic.ini upgrade head
```

## В Kubernetes (ArgoCD)

Каждый Helm-шаблон `migrate-jobs.yaml` рендерит `Job` с аннотациями:

```yaml
argocd.argoproj.io/hook: PreSync
argocd.argoproj.io/sync-wave: "-10"
```

ArgoCD выполняет миграции до Sync основных Deployments:
- sync-wave **-20** — PostgreSQL release (отдельное ArgoCD Application)
- sync-wave **-10** — Migrate Jobs (PreSync hooks)
- sync-wave **0**   — Deployments сервисов

Образ миграции — `harbor.mokryakov.local/education-platform/<svc>-service-migrate:<tag>`,
entrypoint — `alembic -c services/<svc>_service/alembic.ini upgrade head`.

## Откат

Локально — `alembic downgrade -1`.
В кластере — выкатить старый образ сервиса и руками выполнить `alembic downgrade` через Job
(не реализовано автоматически; для production рекомендуется forward-only миграции).
