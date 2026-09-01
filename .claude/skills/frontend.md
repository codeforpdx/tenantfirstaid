# Frontend

Reference for frontend development workflow. Run all commands from `frontend/`.

## Commands

```bash
mise run generate-frontend-assets  # Required before build/typecheck — generates src/types/models.ts and src/generated/referrals.ts
mise run lint              # Lint (eslint)
mise run fmt               # Format (prettier)
mise run typecheck         # Type-check (tsc) — use the typescript-lsp plugin for inline diagnostics
mise run build             # Build (auto-generates frontend assets first)
mise run test              # Run tests (vitest)
mise run test -- --coverage  # With coverage

# Run any check inside the Dockerfile ci image instead of on the host.
mise run check --container            # whole suite in a container (auto engine)
mise run lint --container --engine docker
mise run fmt --container --write      # reformat the host tree via the container
```

Every task above takes `--container` (and `--engine auto|docker|container|podman`). The
lanes differ on purpose in what they mount, which is why the same task can behave
differently on the host and in a container:

| Lane | Mounts | Notes |
|---|---|---|
| `lint`, `typecheck` | source only, into the image's own tree | Dependencies come from the image, so these reproduce CI even if the host `node_modules` is stale or missing. |
| `fmt --write` | repo root | Reformats the host tree in place. Without `--write`, `fmt --container` is verify-only. |
| `build`, `test`, `check` | nothing | Runs the image's baked source; `build --container` verifies only — its `dist/` never reaches the host. |

See `scripts/container_dispatch.sh` for the mount rules and how to name a binary in a
containerized command.

`generate-frontend-assets` automatically handles the backend `uv` requirement via a path splice. Always run it before `typecheck` or `build` — the generated `src/types/models.ts` and `src/generated/referrals.ts` are gitignored.

## Docker

Frontend Dockerfile targets (`frontend/Dockerfile`):

| Target | Purpose |
|---|---|
| `local` | Dev server for local development (default in compose) |
| `ci` | Runs generate-frontend-assets, typecheck, lint, tests, and build |
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
