# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./

FROM base AS deps-prod
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM base AS deps-dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --dev

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=deps-prod /app/.venv /app/.venv
COPY tenantfirstaid ./tenantfirstaid

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--threads", "4", "tenantfirstaid.app:app"]

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS ci

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=deps-dev /app/.venv /app/.venv
COPY . .

# CI systems usually override this command with specific checks.
CMD ["uv", "run", "--dev", "pytest", "-q"]
