# Education Platform

Микросервисная платформа обучения и тестирования сотрудников: пользователь проходит тест,
ответы анализирует LLM (GigaChat / mock), формируется отчёт с рекомендациями.

## Стек

- **Python 3.12**, **FastAPI**, **uvicorn**, **SQLAlchemy 2.0 async**, **asyncpg**, **Alembic**, **PyJWT**, **structlog**, **prometheus-client**, **httpx**, **passlib[bcrypt]**, **pydantic v2 / pydantic-settings**.
- **Frontend**: React 18 + Vite + TypeScript + axios, прод-сборка под `nginx-unprivileged`.
- **Инфраструктура**: PostgreSQL 15 (Bitnami chart), Kubernetes (kubeadm + containerd + Calico + ingress-nginx + MetalLB), Helm, ArgoCD (app-of-apps), Jenkins, Harbor.
- **uv** как менеджер зависимостей; ОДИН корневой `pyproject.toml` с per-service `optional-dependencies` extras.

## Сервисы

| Сервис          | Порт | Назначение                                                  | Схема    |
|-----------------|------|-------------------------------------------------------------|----------|
| api-gateway     | 8080 | Единая точка входа, проксирование, JWT-валидация            | —        |
| auth-service    | 8080 | Регистрация, логин, refresh, выпуск JWT, вызов user `/internal` | `auth`   |
| user-service    | 8080 | Профили сотрудников, отделы, роли                           | `users`  |
| test-service    | 8080 | Создание тестов, попытки, **единственный orchestrator submit-flow** | `tests`  |
| llm-service     | 8080 | LLM-анализ ответов (GigaChat / mock)                        | `llm`    |
| report-service  | 8080 | Итоговые отчёты (JSON/HTML)                                 | `reports`|
| frontend        | 8080 | React SPA, nginx-unprivileged                               | —        |

Все backend-сервисы:
- получают конфиг через env (12-factor),
- эмитят структурные JSON-логи в stdout,
- отдают `/healthz`, `/readyz`, `/metrics`, `/openapi.yaml`, `/docs`,
- запускаются под non-root в multi-stage `python:3.12-slim` образах.

Внутренние эндпоинты (`user-service /internal`, `llm-service /analyze`, `report-service /reports`) защищены `pkg.internal_auth.RequireInternalCaller` — короткоживущим HS256 JWT с
`iss`/`aud`/`exp`. `test-service` — единственный, кто оркеструет вызовы `llm-service` → `report-service`.

## Структура репозитория

```
education-platform/
├── pyproject.toml             # ОДИН корневой проект (uv) + per-service extras
├── Dockerfile                 # общий, multi-stage, ARG SERVICE
├── Dockerfile.migrate         # alembic-only образ, ARG SERVICE
├── docker-compose.yml         # postgres + 6 сервисов + frontend + 5 migrate jobs
├── Jenkinsfile                # declarative pipeline
├── pkg/                       # shared libs (config, logger, db, errors, jwt_auth, internal_auth, http_client, metrics, health, app_factory)
├── services/
│   ├── auth_service/
│   ├── user_service/
│   ├── test_service/
│   ├── llm_service/
│   ├── report_service/
│   └── api_gateway/
├── frontend/                  # React + Vite + TS, prod-Dockerfile (nginx-unprivileged)
├── deploy/
│   ├── argocd/                # app-of-apps: root-app.yaml + applications/{postgresql,education-platform}.yaml
│   └── charts/
│       ├── postgresql/        # отдельный Helm release (sync-wave -20)
│       └── education-platform/ # приложение (sync-wave 0, миграции PreSync sync-wave -10)
├── docs/
│   ├── curl-examples.md       # happy-path curl-команды
│   ├── env.md                 # таблица env-переменных
│   └── migrations.md          # как создавать и применять миграции
└── scripts/
    └── init-db.sql            # bootstrap для локального postgres (роли + схемы)
```

## Быстрый старт локально (Docker Compose)

```bash
cp .env.example .env

# 1. Поднимаем postgres + создаём роли/схемы (init-db.sql выполняется автоматически).
docker compose up -d postgres

# 2. Запускаем миграции (одноразово; повторно — после изменения моделей).
docker compose --profile migrate up --abort-on-container-exit

# 3. Запускаем backend + frontend.
docker compose up -d

# 4. Открываем:
#   http://localhost:13000      — React SPA
#   http://localhost:18080/docs — Swagger api-gateway
#   http://localhost:15432      — postgres (порт хост-системы)
```

Прогон happy-path: `docs/curl-examples.md`.

## Быстрый старт без Docker (uv)

```bash
pip install uv
uv sync --all-extras

# В отдельных терминалах (нужны DB_USER/PASSWORD и роли в Postgres):
uv run uvicorn services.auth_service.app.main:app   --reload --port 18001
uv run uvicorn services.user_service.app.main:app   --reload --port 18002
uv run uvicorn services.test_service.app.main:app   --reload --port 18003
uv run uvicorn services.llm_service.app.main:app    --reload --port 18004
uv run uvicorn services.report_service.app.main:app --reload --port 18005
uv run uvicorn services.api_gateway.app.main:app    --reload --port 18080
```

## Тесты и линт

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .

# Frontend
npm --prefix frontend run lint
npm --prefix frontend test
```

## Сборка Docker-образов

```bash
# Сервис
docker buildx build --build-arg SERVICE=auth_service \
  -t harbor.mokryakov.local/education-platform/auth-service:dev -f Dockerfile .

# Миграционный образ
docker buildx build --build-arg SERVICE=auth_service \
  -t harbor.mokryakov.local/education-platform/auth-service-migrate:dev -f Dockerfile.migrate .

# Frontend
docker buildx build -t harbor.mokryakov.local/education-platform/frontend:dev frontend
```

## Деплой в Kubernetes

1. Поднять PostgreSQL отдельным релизом (`deploy/charts/postgresql`):

   ```bash
   helm dependency update deploy/charts/postgresql
   helm upgrade --install postgresql deploy/charts/postgresql \
     -n database --create-namespace
   ```

2. Положить секреты `jwt-secret`, `internal-jwt-secret`, `gigachat-creds` в namespace `app`.

3. Поднять приложение (`deploy/charts/education-platform`):

   ```bash
   helm upgrade --install education-platform deploy/charts/education-platform \
     -n app --create-namespace
   ```

Через ArgoCD: применить `deploy/argocd/root-app.yaml`, дальше ArgoCD сам рассинкает
`postgresql` (sync-wave -20) → migrate Jobs (PreSync sync-wave -10) → Deployments (wave 0).

## CI/CD (Jenkins → Harbor → ArgoCD)

```
git push origin main
  → Jenkins:
      1. uv sync; ruff check; ruff format --check; pytest
      2. (matrix) docker buildx build --build-arg SERVICE=<svc> + push в Harbor
      3. yq -i '.services.<svc>.image.tag = "<sha>"' в deploy-repo/charts/.../values.yaml
      4. git push deploy-repo
  → ArgoCD: автосинк, PreSync hooks для migrate Jobs, потом Deployments
```

См. `Jenkinsfile`.

## Документация

- `docs/env.md` — все env-переменные.
- `docs/curl-examples.md` — happy-path curl.
- `docs/migrations.md` — Alembic в локальном dev и в k8s.
- `/docs`, `/redoc`, `/openapi.yaml` отдаёт каждый сервис.

## Troubleshooting

| Симптом                                              | Что проверить                                         |
|------------------------------------------------------|-------------------------------------------------------|
| `readyz` отдаёт 503 / `db_ready` failures            | `DB_*`, что роль и схема созданы, что миграции применены |
| `/api/v1/auth/register` падает 502 / `UPSTREAM_ERROR`| user-service не отвечает / неправильный `USER_SERVICE_URL` / просрочен `INTERNAL_JWT_SECRET` (должен совпадать на всех сервисах) |
| `submit` зависает или 502                            | проверь логи test-service → llm-service (`LLM_PROVIDER`, `LLM_API_KEY`) → report-service |
| Pod в k8s не резолвит `postgres-service`             | NetworkPolicy `allow-dns` отсутствует или `kube-dns` имеет другой selector. См. `charts/education-platform/templates/networkpolicies.yaml`. |
| Pod падает с `psycopg2.OperationalError: SSL ...`     | `DB_SSL_MODE=disable` для in-cluster postgres, либо проставить корректный SSL-параметр |
| `python: command not found` в migrate Job            | у нас `tini` + `alembic` через venv; убедитесь что используете `Dockerfile.migrate`, а не сторонний образ |
| `403 FORBIDDEN: Role 'employee' is not allowed`      | Эндпоинт ограничен ролями `manager`/`admin` — проверьте role в JWT (`/api/v1/auth/me`) |

## Лицензия

Proprietary.
