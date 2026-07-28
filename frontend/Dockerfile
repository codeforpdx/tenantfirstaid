ARG PORT=5173

# -----------------------------------------------
# base: install deps and copy source
# -----------------------------------------------
FROM oven/bun:1.3.14-slim@sha256:d56a2534ffd262e92c12fd3249d3924d296d97086da773f821d7d0477435ea04 AS base

WORKDIR /workspace/frontend

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/* \
    # json2ts (used by `bun run generate-types`) has a `#!/usr/bin/env node`
    # shebang; bun-slim has no `node` binary, so alias it to `bun` — Bun's
    # documented drop-in-for-Node approach.
    && ln -s "$(command -v bun)" /usr/local/bin/node

COPY --from=ghcr.io/astral-sh/uv@sha256:798712e57f879c5393777cbda2bb309b29fcdeb0532129d4b1c3125c5385975a /uv /usr/local/bin/uv

COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
COPY backend/ ../backend/

# -----------------------------------------------
# local: dev server for local development
# -----------------------------------------------
FROM base AS local

ARG PORT
ENV PORT=${PORT}

EXPOSE ${PORT}

CMD ["sh", "-c", "bun run generate-types && bun run dev -- --host 0.0.0.0 --port ${PORT}"]

# -----------------------------------------------
# ci: run all checks and build
# -----------------------------------------------
FROM base AS ci

CMD ["sh", "-c", "bun run generate-types && bun run typecheck && bun run lint && bun run test -- --run && bun run build"]

# -----------------------------------------------
# production-build: compile static assets
# -----------------------------------------------
FROM base AS production-build

RUN bun run generate-types && bun run build

# -----------------------------------------------
# production: minimal image to serve static files
# -----------------------------------------------
FROM oven/bun:1.3.14-slim@sha256:d56a2534ffd262e92c12fd3249d3924d296d97086da773f821d7d0477435ea04 AS production

ARG PORT
ENV PORT=${PORT}

WORKDIR /app

COPY --from=production-build /workspace/frontend/dist ./dist

ENV BUN_INSTALL=/usr/local/bun
ENV PATH="${BUN_INSTALL}/bin:${PATH}"

RUN bun install -g --ignore-scripts serve@14 \
    && useradd --system --no-create-home appuser \
    && chown -R appuser /app
USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "serve -s dist -l ${PORT}"]
