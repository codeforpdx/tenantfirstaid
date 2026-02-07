# syntax=docker/dockerfile:1
ARG TYPE=deploy

# ─────────────────────────────────────────────────────────────
# Base stage - common setup
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# ─────────────────────────────────────────────────────────────
# Dev stage - full tooling
# ─────────────────────────────────────────────────────────────
FROM base AS dev

# Install all dependencies including dev group
RUN uv sync

# Copy all source code and tests
COPY tenantfirstaid/ ./tenantfirstaid/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY Makefile ./

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

# Install only production dependencies
RUN uv sync --no-dev

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
