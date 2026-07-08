# Onboarding

Help a new contributor get the repo set up and running locally for the first time.

## Prerequisites

### GitHub account + commit signing

- Join the [Code PDX Contributor team](https://www.codepdx.org/volunteer) (step 2: Connect on Discord & Request Access). You'll receive a GitHub invitation email — accept it.
- Enable [commit signing](https://docs.github.com/authentication/managing-commit-signature-verification) in your GitHub account settings (SSH and GPG keys). GPG is typical.

### mise (dev toolchain manager)

[mise](https://mise.jdx.dev/) provisions and pins the repo's toolchain — `uv` (backend Python), `node` (frontend), and, on macOS, the [apple/container](https://github.com/apple/container) engine — so you don't install them individually.

```sh
# Install mise: https://mise.jdx.dev/installing-mise.html
```

### Google Cloud application default credentials

Required to run the backend locally (Gemini LLM + Vertex AI RAG). A project admin must grant your Google account access first — ask in Discord #tenantfirstaid-general.

Once granted:

```sh
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install
gcloud auth application-default login
gcloud auth application-default set-quota-project tenantfirstaid
```

Note the credentials file path — typically `~/.config/gcloud/application_default_credentials.json` on Unix. Do not use `~` in path values; Python won't expand it.

### LangSmith API key

Sign up for a free [LangSmith](https://smith.langchain.com/) account and generate an API key from your account settings.

---

## Starting the app

First set up the backend env file (both options below read it):

```sh
cp backend/.env.example backend/.env
# Set GOOGLE_APPLICATION_CREDENTIALS (the creds path from above) and LANGSMITH_API_KEY.
```

### Option A: Containers (fastest, cross-engine)

Runs the whole stack in containers — no host Python/Node needed. Uses apple/container on macOS, Docker elsewhere.

```sh
mise trust && mise install   # provision the container engine (apple/container on macOS)
mise run container start      # macOS only; on Linux make sure Docker is running
mise run dev --container      # builds + runs both services, then prints the URL to open
```

Open the printed URL — `http://localhost:5173` on Docker, or a `http://192.168.64.x:5173` address on apple/container (which has no localhost port-publishing, so you browse the container's IP directly). Ctrl-C stops the stack.

### Option B: Host (best for active development — live reload, editor tooling)

```sh
mise trust && mise run setup  # provision toolchains, install deps, generate types
mise run dev                  # start backend + frontend on the host
```

Open http://localhost:5173 and start chatting.

### Also available: docker-compose

`docker-compose.yml` is the canonical Docker multi-service definition. Unlike the tasks above it reads the **root** `.env` and bind-mounts the creds file via `GCP_CREDENTIALS_FILE`:

```sh
cp .env.example .env          # set GCP_CREDENTIALS_FILE to your creds JSON path
cp backend/.env.example backend/.env   # set LANGSMITH_API_KEY
docker compose up --build     # backend :5001, frontend :5173
# override targets to run CI checks in Docker: RUNTIME_TARGET=ci FRONTEND_TARGET=ci docker compose up --build
```

---

## Running checks

Checks are driven by [mise](https://mise.jdx.dev), configured as a monorepo: the root
`mise.toml` ties together `backend/mise.toml` (uv toolchain) and `frontend/mise.toml`
(node toolchain). One-time setup provisions the pinned tools (uv, node 24, and — on
macOS — apple/container):

```sh
# Install mise: https://mise.jdx.dev/installing-mise.html
# The setup task provisions both toolchains, installs deps, and generates types.
# (Tools install per project config, so a bare root `mise install` would miss the
# frontend's node — the task runs `mise -C backend/frontend install` for you.)
mise trust && mise run setup
```

Then run the checks on the host (the fast, default path):

```sh
mise run check              # everything (backend + frontend)
mise run //backend:check    # backend only: clean, sync, fmt, lint, typecheck, test
mise run //backend:test     # a single backend check
mise run //frontend:check   # frontend only
```

From inside a project directory the bare name works too (`cd backend && mise run test`).

### Running a check in a container instead

Every check takes an opt-in `--container` flag that runs that same check inside the
Dockerfile `ci` stage instead of on the host. It auto-detects an engine; `--engine`
forces one (`docker`, `container` for apple/container, or `podman`):

```sh
mise run //backend:test --container                     # auto-detected engine
mise run //backend:check --container --engine container # whole suite via apple/container
mise run //frontend:check --container --engine docker   # frontend suite via Docker
```

The container lane verifies formatting rather than rewriting it (mutate on the host,
verify in the container), so `fmt`/`check --container` run `ruff format --check`.

**Claude Code users:** this project enables the Claude Code sandbox (for network-egress
confinement). The sandbox blocks two things: container engines (Docker and apple/container
both return `Operation not permitted`, and no committed project setting can lift that —
sandbox exclusions are honored only from your personal `~/.claude/settings.json`), and
mise's own tool provisioning / `mise trust` (writes under `~/.local/{share,state}/mise`).
So do the one-time `mise run setup` yourself, then let Claude run the host-lane checks
(`mise run //backend:check`, etc.); run any `--container` checks yourself or leave them to CI.

---

## Getting help

- Discord: #tenantfirstaid-general in the [Code PDX server](https://www.codepdx.org/)
- Meetups: https://www.meetup.com/codepdx/
