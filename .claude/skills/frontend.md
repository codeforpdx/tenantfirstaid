# Frontend

Reference for frontend development workflow. Run all commands from `frontend/`.

## Commands

```bash
npm run generate-types    # Required before build/typecheck — generates src/types/models.ts
npm run lint              # Lint (eslint)
npm run format            # Format (prettier)
npm run typecheck         # Type-check (tsc) — use the typescript-lsp plugin for inline diagnostics
npm run build             # Build (auto-generates types first)
npm run test -- --run     # Run tests (vitest)
npm run test -- --run --coverage  # With coverage
```

`generate-types` requires `uv` to be installed. It runs the backend Python to emit JSON Schema, piped through `json2ts`. Always run it before `typecheck` or `build` — the generated `src/types/models.ts` is gitignored.

## Docker

Frontend Dockerfile targets (`frontend/Dockerfile`):

| Target | Purpose |
|---|---|
| `local` | Dev server for local development (default in compose) |
| `ci` | Runs generate-types, typecheck, lint, tests, and build |
| `production` | Minimal image serving built static files via `serve` |
| `production-build` | Compiles static assets (intermediate stage) |

Build a specific target:

```sh
# Dev server
docker build -f frontend/Dockerfile --target local -t tenantfirstaid-frontend:local .

# Production static server
docker build -f frontend/Dockerfile --target production -t tenantfirstaid-frontend:production .
```

Override the frontend target in compose:

```sh
FRONTEND_TARGET=ci docker compose up --build
```

Note: Safari blocks the `http://localhost:5173` redirect from compose. Use Chrome or Vivaldi.
