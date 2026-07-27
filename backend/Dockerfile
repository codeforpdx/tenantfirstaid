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

COPY --from=deps-dev /app/.venv /app/.venv
COPY . .

# CI systems usually override this command with specific checks.
CMD ["uv", "run", "--dev", "pytest", "-q"]

# -----------------------------------------------
# docs: ci + the great-docs toolchain (Quarto, harper-cli)
# -----------------------------------------------
# Kept separate from `ci` so the lint/typecheck/test lanes stay lean; only the
# `docs*` mise tasks build this stage (via --target docs). See the `docs`,
# `docs-lint`, `docs-check-links`, and `docs-proofread` tasks in mise.toml.
FROM ci AS docs

# Quarto is the rendering engine behind `great-docs build`. It ships as an
# arch-specific .deb; pick the matching one via dpkg's architecture and let apt
# resolve the deb's own dependencies. curl/ca-certificates are also needed to
# fetch harper-cli below. Pinned for reproducibility — bump with the host toolchain.
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

# harper-cli powers `great-docs proofread` (spelling/grammar). It ships as a single
# prebuilt binary per arch; map dpkg's architecture to the matching gnu tarball.
# Pinned for reproducibility — bump alongside the toolchain.
ARG HARPER_VERSION=2.6.0
RUN arch="$(dpkg --print-architecture)" && \
    case "$arch" in \
      amd64) triple="x86_64-unknown-linux-gnu" ;; \
      arm64) triple="aarch64-unknown-linux-gnu" ;; \
      *) echo "unsupported architecture for harper-cli: $arch" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/harper-cli.tar.gz \
      "https://github.com/Automattic/harper/releases/download/v${HARPER_VERSION}/harper-cli-${triple}.tar.gz" && \
    tar -xzf /tmp/harper-cli.tar.gz -C /usr/local/bin harper-cli && \
    rm -f /tmp/harper-cli.tar.gz && \
    chmod 0755 /usr/local/bin/harper-cli && \
    harper-cli --version
