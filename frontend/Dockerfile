FROM node:22-bookworm-slim AS base

WORKDIR /workspace/frontend

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
COPY backend/ ../backend/

FROM base AS local

EXPOSE 5173

CMD ["sh", "-c", "npm run generate-types && npm run dev -- --host 0.0.0.0 --port 5173"]

FROM base AS ci

CMD ["sh", "-c", "npm run generate-types && npm run typecheck && npm run lint && npm run test -- --run && npm run build"]

FROM base AS production-build

RUN npm run generate-types && npm run build

FROM node:22-bookworm-slim AS production

WORKDIR /app

COPY --from=production-build /workspace/frontend/dist ./dist

RUN npm install -g serve@14

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
