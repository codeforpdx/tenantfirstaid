# syntax=docker/dockerfile:1.7

ARG PORT=5001

# -----------------------------------------------
# base: common environment and UV configuration
# -----------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./

# -----------------------------------------------
# deps-prod: install production dependencies only
# -----------------------------------------------
FROM base AS deps-prod
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -----------------------------------------------
# deps-dev: install all dependencies (incl. dev)
# -----------------------------------------------
FROM base AS deps-dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --dev

# -----------------------------------------------
# runtime: lean production image
# -----------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca AS runtime

ARG PORT
ENV PORT=${PORT}

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# copy production .venv w/o UV cache
COPY --from=deps-prod /app/.venv /app/.venv
COPY tenantfirstaid ./tenantfirstaid

RUN useradd --system --no-create-home appuser
USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 tenantfirstaid.app:app"]

# -----------------------------------------------
# ci: full dev environment for running checks
# -----------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca AS ci

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Quarto is the rendering engine behind `great-docs build` (see the `docs` mise task).
# It ships as an arch-specific .deb; pick the matching one via dpkg's architecture and
# let apt resolve the deb's own dependencies. Pinned for reproducibility — bump in step
# with the host toolchain.
ARG QUARTO_VERSION=1.9.38
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    arch="$(dpkg --print-architecture)" && \
    curl -fsSL -o /tmp/quarto.deb \
      "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-${arch}.deb" && \
    apt-get install -y --no-install-recommends /tmp/quarto.deb && \
    rm -f /tmp/quarto.deb && \
    quarto --version

COPY --from=deps-dev /app/.venv /app/.venv
COPY . .

# CI systems usually override this command with specific checks.
CMD ["uv", "run", "--dev", "pytest", "-q"]
