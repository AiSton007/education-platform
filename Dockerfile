# syntax=docker/dockerfile:1.7
# Common Dockerfile for every FastAPI service in the monorepo.
# Pick a service with --build-arg SERVICE=auth_service (etc.).

ARG PYTHON_BASE_IMAGE=harbor.mokryakov.local/library/education-python-base:3.12

# ---------- builder ----------
FROM ${PYTHON_BASE_IMAGE} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /workspace

# Copy only metadata first to maximise layer cache hit ratio.
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

# Now copy the source and create a wheel-less install of the project itself.
COPY pkg ./pkg
COPY services ./services
RUN uv sync --no-dev

# ---------- runtime ----------
FROM ${PYTHON_BASE_IMAGE} AS runtime

ARG SERVICE
ENV SERVICE=${SERVICE} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV=/opt/venv

RUN groupadd --system --gid 65532 app \
    && useradd --system --uid 65532 --gid app --home /home/app --shell /usr/sbin/nologin app \
    && mkdir -p /home/app \
    && chown -R app:app /home/app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /workspace /workspace

WORKDIR /workspace

USER 65532:65532

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]

# SERVICE arg is baked in via env; uvicorn locates the corresponding ASGI app.
CMD ["sh", "-c", "uvicorn services.${SERVICE}.app.main:app --host 0.0.0.0 --port 8080 --workers 1 --no-access-log"]
