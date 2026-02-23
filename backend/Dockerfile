# syntax=docker/dockerfile:1
ARG TYPE=deploy

# ─────────────────────────────────────────────────────────────
# Base stage - common setup
# ─────────────────────────────────────────────────────────────
# Use Astral's image with pre-installed UV and Python 3.13
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim AS base

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# ─────────────────────────────────────────────────────────────
# Dev stage - full tooling
# ─────────────────────────────────────────────────────────────
FROM base AS dev

# Install system dependencies (e.g. make)
RUN apt-get update && apt-get install -y --no-install-recommends \
        make \
    && rm -rf /var/lib/apt/lists/*

# Install all dependencies including dev group
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --frozen

# Copy all source code and tests
COPY tenantfirstaid/ ./tenantfirstaid/
COPY scripts/        ./scripts/
COPY tests/          ./tests/
COPY Makefile        ./

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV FLASK_ENV=development
ENV ENV=dev
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Use Flask dev server for hot reload
CMD ["uv", "run", "python", "-m", "tenantfirstaid.app"]

# ─────────────────────────────────────────────────────────────
# Deploy stage - minimal production
# ─────────────────────────────────────────────────────────────
FROM base AS deploy

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install only production dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen

# Copy only application code (no tests)
COPY tenantfirstaid/ ./tenantfirstaid/
# Copy documents for RAG ingestion if needed
COPY scripts/documents/ ./scripts/documents/

ENV FLASK_ENV=production
ENV ENV=prod
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Production uses Gunicorn
CMD ["uv", "run", "gunicorn", \
     "--timeout", "300", \
     "--capture-output", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "-w", "4", \
     "-b", "0.0.0.0:5000", \
     "tenantfirstaid.app:app"]

# ─────────────────────────────────────────────────────────────
# Final stage selection
# ─────────────────────────────────────────────────────────────
FROM ${TYPE} AS final
