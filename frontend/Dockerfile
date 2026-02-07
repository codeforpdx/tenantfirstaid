# syntax=docker/dockerfile:1
ARG TYPE=deploy

# ─────────────────────────────────────────────────────────────
# Builder stage - compile TypeScript and build assets
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─────────────────────────────────────────────────────────────
# Dev stage - Vite dev server with hot reload
# ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS dev

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ─────────────────────────────────────────────────────────────
# Deploy stage - nginx serving static files
# ─────────────────────────────────────────────────────────────
FROM nginx:alpine AS deploy

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create nginx config for SPA routing
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Serve static files
    location / {
        try_files $uri /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

EXPOSE 80

# ─────────────────────────────────────────────────────────────
# Final stage selection
# ─────────────────────────────────────────────────────────────
FROM ${TYPE} AS final
