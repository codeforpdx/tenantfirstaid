# Tenant First Aid

A chatbot that provides legal information related to housing and eviction in Oregon.

Live at https://tenantfirstaid.com/

## Local Development

[![PR Checks](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml)
[![CI-CD (Production)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.production.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.production.yml)

| 💡 Using Claude Code? Type `/onboarding` in the Claude Code UI for guided setup assistance. |
|---|

### Prerequisites

<details>
<summary>GitHub account</summary>

- You will need a GitHub account (free) to contribute to the project.  No account is necessary to browse the source code.
  - You will be invited to join the [Contributor](https://github.com/orgs/codeforpdx/teams/contributor) team after you complete [step 2 ("Connect on Discord & Request Access") of the Code PDX onboarding](https://www.codepdx.org/volunteer)
  - Look for the invitation email and click the link in the email to accept the invitation.
  - You will also have to enable [commit signing](https://docs.github.com/authentication/managing-commit-signature-verification) by adding a key (typically `GPG`) to your GitHub account (click on your avatar -> Settings -> SSH and GPG keys).
</details>

<details>
<summary>mise</summary>

- This repo is a [mise](https://mise.jdx.dev) monorepo. `mise` provisions and pins the rest of the toolchain for you — `uv` (backend Python deps/tools) and `node`/`npm` (frontend) — and wires up the dev tasks used throughout this README.
[Install mise](https://mise.jdx.dev/getting-started.html)
</details>

<details>
<summary>Google Cloud application default credentials file</summary>

- This is needed to spin up a local instance of the backend (i.e. API calls to the chat LLM and RAG agent).
- The chatbot now uses Google Gemini (previously OpenAI's ChatGPT).
- The `tenantfirstaid` Google project admin will need to manually assign a role to you (gmail account).  Reach out in the Discord channel #[tenantfirstaid-general](https://discord.com/channels/1068260532806766733/1367177752792531115) to arrange this.
- You need to authenticate with the gcloud CLI to develop. `gcloud` is pinned as a per-task tool in the root `mise.toml`, so it's provisioned on first use — no separate install:
    1. `mise run //:gcloud-login` (root-qualified) — runs `gcloud auth application-default login` + `set-quota-project`, then prints the resulting [application default credentials](https://cloud.google.com/docs/authentication/application-default-credentials) file path
    1. add the printed path as `GOOGLE_APPLICATION_CREDENTIALS=<PATH_TO_CREDS>` to your `backend/.env` file (HINT: don't use path shortcuts like `~` for home, python won't be able to find it).
</details>

<details>
<summary>LangChain/LangSmith</summary>

- [langsmith](https://docs.langchain.com/langsmith/create-account-api-key) *Developer* (free) or *Plus* account and API key
</details>

### Quick Start

1. clone repo
1. copy `backend/.env.example` to a new file named `.env` in the same directory.
   1. set `GOOGLE_APPLICATION_CREDENTIALS` as per [Google Cloud application default credentials file](#prerequisites) (requires the project admin to have already granted your Google account access, per that section)
   1. set `LANGSMITH_API_KEY` as per [LangChain/LangSmith](#prerequisites)
1. `mise run setup` (from the repo root; one-time: provisions the backend/frontend toolchains, installs deps, and generates frontend assets)
   - on a fresh clone mise will prompt to trust the repo's config — run `mise trust` if prompted
1. (optional) smoke-test your Google Cloud credentials before starting the app: `mise run //:gcloud-login-check` — it loads `GOOGLE_APPLICATION_CREDENTIALS` from `backend/.env` the same way the app does and queries the same Vertex AI Search serving config
1. `mise run dev` (starts the backend API and frontend dev server together)
   - or in two separate terminals: `mise run //backend:serve` and `mise run //frontend:dev`
1. Go to http://localhost:5173
1. Start chatting

| 💡 Using Claude Code? Type `/backend` in the Claude Code UI for backend workflow reference. |
|---|

### Backend Development & Checks

1. change to the `backend/` directory
   ```sh
   % cd backend
   ```

- run individual checks

  1. _format_ Python code with `ruff`
     ```sh
     % mise run fmt
     ```
  1. _lint_ Python code with `ruff`
     ```sh
     % mise run lint
     ```
  1. _typecheck_ Python code with `ty`

     ```sh
     % mise run typecheck
     ```

     _typecheck_ with other Python typecheckers which are not protected in [PR Checks](.github/workflows/pr-check.yml) - useful for completeness & a 2nd opinion

     1. _typecheck_ Python code with `mypy`
        ```sh
        % mise run typecheck --checker mypy
        ```
     1. _typecheck_ Python code with `pyrefly`
        ```sh
        % mise run typecheck --checker pyrefly
        ```

  1. _test_ Python code with `pytest`
     ```sh
     % mise run test
     ```

  To pass extra flags straight through to the underlying tool, `lint`, `typecheck`, and `test` all accept trailing args after `--`, e.g.
  ```sh
  % mise run lint -- --fix
  % mise run test -- -k test_some_name -v
  ```
  This is preferred over `mise exec -- uv run <tool> ...`, which bypasses the `sync` dependency and can silently run against a stale `.venv` after a dependency bump.

- or run the above checks in one-shot
  ```sh
  % mise run check
  ```
  (equivalent to `mise run //backend:check` from the repo root). `check` runs `lint`, `typecheck`, and `test` concurrently (after `fmt`), so all three report even if one fails — you see every failure in a single run rather than stopping at the first.

  To run both backend and frontend checks together, use `mise run check` from the repo root.

- build and browse the backend user guide (needs [Quarto](https://quarto.org), or add `--container`)
  ```sh
  % mise run docs
  % mise run docs-serve
  ```
  | 💡 On MacOS `docs-serve` will open Safari but can't access the local URL.  Open the URL on a Chrome/Chromium-based browser. |

  `docs-lint`, `docs-check-links`, and `docs-proofread` (or `docs-check` for all three) catch missing docstrings, broken links, and spelling/grammar issues; see the [Command Reference](backend/developer_guide/08-command-reference.qmd) chapter.

| 💡 Using Claude Code? Type `/backend` in the Claude Code UI for backend workflow reference (including docs). |
|---|

### Frontend Development & Checks

1. change to the `frontend/` directory
   ```sh
   % cd frontend
   ```

1. generate frontend types and referral data from the backend (required before type-checking, testing, or building)
   ```sh
   % mise run //backend:generate-frontend-assets
   ```
   (root-qualified since this splices the frontend's `node`/`json2ts` onto the backend's `PATH`; see `backend/mise.toml`. Re-run this any time the backend Pydantic models or referral catalog change. `mise run //:setup` also does this, plus a full toolchain provision/install — use that instead only when you need the heavier one-time setup.)

   This writes `src/types/models.ts` from the backend Pydantic models and `src/generated/referrals.ts` from the validated referral catalog. Both outputs are gitignored. Non-generated frontend types are stored in `src/shared/types/` and are checked into source control.

- run individual checks

  1. _lint_ TypeScript code with `eslint`
     ```sh
     % mise run lint
     ```
  1. _typecheck_ TypeScript code with `tsc`
     ```sh
     % mise run typecheck
     ```
  1. _test_ TypeScript code with `vitest`
     ```sh
     % mise run test
     ```

  Each accepts extra flags after `--`, e.g. `mise run lint -- --fix`, the same as the backend checks above — and unlike `mise exec`, keeps `npm install` (via the `install` task's dependency) up to date if the lockfile changed.

- or run the above checks in one-shot (also regenerates frontend assets first)
  ```sh
  % mise run check
  ```
  (equivalent to `mise run //frontend:check` from the repo root; see the backend section above for running both together)

| 💡 Using Claude Code? Type `/backend` or `/frontend` in the Claude Code UI for Docker target reference, or `/onboarding` for the compose quick start. |
|---|

### Docker

The mise-way to spin up a local deployment of the app in containers (builds the `runtime`/`local` targets below for you, then starts and wires up both services) is:

```sh
% mise run dev --container
```

This is engine-agnostic (Docker, Podman, or apple/container — auto-detected; override with `--engine`) and is a cross-engine stand-in for `docker compose`.

Separately, the checks (`//backend:check`, `//frontend:check`) each accept their own `--container` flag to build and run that check suite against the `ci` target instead of your host toolchain — useful for reproducing a CI failure locally, not for running the app itself.

The project has separate Dockerfiles for backend and frontend, each with multiple build stages, if you need to build an image directly. Use `--target` to pick a stage:

```sh
# backend runtime (serves API)
docker build -f backend/Dockerfile --target runtime -t tenantfirstaid-backend:runtime backend

# frontend local/dev server
docker build -f frontend/Dockerfile --target local -t tenantfirstaid-frontend:local .

# frontend production (serves built static app)
docker build -f frontend/Dockerfile --target production -t tenantfirstaid-frontend:production .
```

#### Docker Compose (quick start)

Copy the root-level env file before running compose:

```sh
cp .env.example .env
```

`GCP_CREDENTIALS_FILE` in this file is a host path to your GCP credentials JSON (the same file referenced by `GOOGLE_APPLICATION_CREDENTIALS` in `backend/.env`). Compose bind-mounts it into the container — it is not injected as an app environment variable.

Then start both services:

```sh
docker compose up --build
```

By default, compose uses:

- backend target: `runtime`
- frontend target: `local`

Override targets at runtime:

```sh
RUNTIME_TARGET=ci FRONTEND_TARGET=ci docker compose up --build
```

Stop services:

```sh
docker compose down
```

## Contributing

We currently have regular project meetups: https://www.meetup.com/codepdx/ . Also check out https://www.codepdx.org/ to find our Discord server.

## Deployment

For information on how the application is deployed, where it runs, how to debug issues, and who has access, see [Deployment.md](Deployment.md).
