# Переменные окружения

## Общие (для всех Python-сервисов)

| Переменная             | Дефолт                 | Описание                                            |
|------------------------|------------------------|-----------------------------------------------------|
| `APP_NAME`             | `<сервис>`             | Имя сервиса в логах/метриках, audience внутр. JWT   |
| `APP_ENV`              | `development`          | окружение (`development`/`staging`/`production`)    |
| `APP_PORT`             | `8080`                 | порт, на котором слушает uvicorn                    |
| `LOG_LEVEL`            | `info`                 | `debug`/`info`/`warning`/`error`                    |
| `METRICS_ENABLED`      | `true`                 | вкл/выкл `/metrics`                                 |
| `CORS_ALLOW_ORIGINS`   | `*`                    | через запятую                                       |

## DB (все сервисы кроме `api-gateway`)

| Переменная              | Дефолт            | Описание                                  |
|-------------------------|-------------------|-------------------------------------------|
| `DB_HOST`               | `postgres`        | host postgres                             |
| `DB_PORT`               | `5432`            |                                            |
| `DB_NAME`               | `education`       | имя базы                                  |
| `DB_USER`               | —                 | per-service пользователь (см. ниже)       |
| `DB_PASSWORD`           | —                 | per-service пароль                        |
| `DB_SCHEMA`             | `<svc>`           | схема внутри базы                         |
| `DB_MAX_OPEN_CONNS`     | `10`              |                                            |
| `DB_MAX_IDLE_CONNS`     | `2`               |                                            |
| `DB_CONN_MAX_LIFETIME`  | `300`             | секунды                                   |

### Per-service ролей в Postgres

| Сервис          | DB user       | Схема    |
|-----------------|---------------|----------|
| auth-service    | `auth_user`   | `auth`   |
| user-service    | `users_user`  | `users`  |
| test-service    | `tests_user`  | `tests`  |
| llm-service     | `llm_user`    | `llm`    |
| report-service  | `reports_user`| `reports`|

В k8s — Secrets `auth-db`, `users-db`, `tests-db`, `llm-db`, `reports-db` (создаются
chart `postgresql`).

## JWT (user)

| Переменная                | Дефолт                     |
|---------------------------|----------------------------|
| `JWT_SECRET`              | (обязательная переменная)  |
| `JWT_ALGORITHM`           | `HS256`                    |
| `JWT_ACCESS_TOKEN_TTL`    | `900`                      |
| `JWT_REFRESH_TOKEN_TTL`   | `604800`                   |
| `JWT_ISSUER`              | `education-platform`       |

## Internal JWT (service-to-service)

| Переменная                | Дефолт                     |
|---------------------------|----------------------------|
| `INTERNAL_JWT_SECRET`     | (обязательная переменная)  |
| `INTERNAL_JWT_ALGORITHM`  | `HS256`                    |
| `INTERNAL_JWT_TTL`        | `300`                      |

## LLM (только `llm-service`)

| Переменная             | Дефолт                                              |
|------------------------|-----------------------------------------------------|
| `LLM_PROVIDER`         | `mock`                                              |
| `LLM_API_URL`          | `https://gigachat.devices.sberbank.ru/api/v1`       |
| `LLM_OAUTH_URL`        | `https://ngw.devices.sberbank.ru:9443/api/v2/oauth` |
| `LLM_OAUTH_SCOPE`      | `GIGACHAT_API_PERS`                                 |
| `LLM_API_KEY`          | base64(`client_id:client_secret`)                   |
| `LLM_MODEL`            | `GigaChat`                                          |
| `LLM_TIMEOUT_SECONDS`  | `30`                                                |
| `LLM_VERIFY_SSL`       | `true`                                              |

## URLs для service-to-service и api-gateway

| Переменная             | Использует                                    |
|------------------------|-----------------------------------------------|
| `AUTH_SERVICE_URL`     | api-gateway                                   |
| `USER_SERVICE_URL`     | api-gateway, auth-service                     |
| `TEST_SERVICE_URL`     | api-gateway                                   |
| `LLM_SERVICE_URL`      | test-service                                  |
| `REPORT_SERVICE_URL`   | api-gateway, test-service                     |
