ARG PORT=5173

# -----------------------------------------------
# base: install deps and copy source
# -----------------------------------------------
FROM node:24-bookworm-slim@sha256:03eae3ef7e88a9de535496fb488d67e02b9d96a063a8967bae657744ecd513f2 AS base

WORKDIR /workspace/frontend

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv@sha256:798712e57f879c5393777cbda2bb309b29fcdeb0532129d4b1c3125c5385975a /uv /usr/local/bin/uv

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
COPY backend/ ../backend/

# -----------------------------------------------
# local: dev server for local development
# -----------------------------------------------
FROM base AS local

ARG PORT
ENV PORT=${PORT}

EXPOSE ${PORT}

CMD ["sh", "-c", "npm run generate-types && npm run dev -- --host 0.0.0.0 --port ${PORT}"]

# -----------------------------------------------
# ci: run all checks and build
# -----------------------------------------------
FROM base AS ci

CMD ["sh", "-c", "npm run generate-types && npm run typecheck && npm run lint && npm run test -- --run && npm run build"]

# -----------------------------------------------
# production-build: compile static assets
# -----------------------------------------------
FROM base AS production-build

RUN npm run generate-types && npm run build

# -----------------------------------------------
# production: minimal image to serve static files
# -----------------------------------------------
FROM node:24-bookworm-slim@sha256:03eae3ef7e88a9de535496fb488d67e02b9d96a063a8967bae657744ecd513f2 AS production

ARG PORT
ENV PORT=${PORT}

WORKDIR /app

COPY --from=production-build /workspace/frontend/dist ./dist

RUN npm install -g --ignore-scripts serve@14 \
    && useradd --system --no-create-home appuser \
    && chown -R appuser /app
USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "serve -s dist -l ${PORT}"]
