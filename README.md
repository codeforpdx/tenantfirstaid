# Tenant First Aid

A chatbot that provides legal information related to housing and eviction in Oregon.

Live at https://tenantfirstaid.com/

## Local Development

[![PR Checks](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml)
[![CI-CD](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.yml)

### Prerequisites

<details>
<summary>GitHub account</summary>

- You will need a GitHub account (free) to contribute to the project.  No account is necessary to browse the source code.
</details>

<details>
<summary>Astral UV</summary>

- `uv` is used in the *backend* to install/manage Python dependencies and run Python sub-tools (e.g. `pytest`)
[Install uv](https://docs.astral.sh/uv/getting-started/installation/)
</details>

<details>
<summary>Google Cloud application default credentials file</summary>

- The chatbot now uses Google Gemini instead of OpenAI. You need to authenticate with the gcloud cli to develop, following these instructions:
    1. [install gcloud](https://cloud.google.com/sdk/docs/install)
    1. [generate application default credentials file](https://cloud.google.com/docs/authentication/application-default-credentials)
    1. `gcloud auth application-default login`
    1. `gcloud auth application-default set-quota-project tenantfirstaid`
    1. add `GOOGLE_APPLICATION_CREDENTIALS=<PATH_TO_CREDS>` to your `backend/.env` file. The default path will be something like `/home/<USERNAME>/.config/gcloud/application_default_credentials.json` on Unix systems. (HINT: don't use path shortcuts like `~` for home, python won't be able to find it).
</details>

<details>
<summary>LangChain/LangSmith</summary>

- [langsmith](https://docs.langchain.com/langsmith/create-account-api-key) *Developer* (free) or *Plus* account and API key
</details>

### Quick Start

1. clone repo
1. copy `backend/.env.example` to a new file named `.env` in the same directory.
   1. set `GOOGLE_APPLICATION_CREDENTIALS` as per [Google Cloud application default credentials file](#prerequisites)
   1. set `LANGSMITH_API_KEY` as per [LangChain/LangSmith](#prerequisites)
1. `cd backend`
1. `uv sync`
1. `uv run python -m tenantfirstaid.app`
1. Open a new terminal / tab
1. `cd ../frontend`
1. `npm install`
1. `npm run dev`
1. Go to http://localhost:5173
1. Start chatting

### Backend Development & Checks

1. change to the `backend/` directory
   ```sh
   % cd backend
   ```

- run individual checks

  1. _format_ Python code with `ruff`
     ```sh
     % uv run ruff format
     ```
     or
     ```sh
     % make fmt
     ```
  1. _lint_ Python code with `ruff`
     ```sh
     % uv run ruff check
     ```
     or
     ```sh
     % make lint
     ```
  1. _typecheck_ Python code with `ty`

     ```sh
     % uv run ty check
     ```

     or

     ```sh
     % make typecheck
     ```

     _typecheck_ with other Python typecheckers which are not protected in [PR Checks](.github/workflows/pr-check.yml) - useful for completeness & a 2nd opinion

     1. _typecheck_ Python code with `mypy`
        ```sh
        % uv run mypy -p tenantfirstaid --python-executable .venv/bin/python3 --check-untyped-defs
        ```
        or
        ```sh
        % make typecheck-mypy
        ```
     1. _typecheck_ Python code with `pyrefly`
        ```sh
        % uv run pyrefly check --python-interpreter .venv/bin/python3
        ```
        or
        ```sh
        % make typecheck-pyrefly
        ```

  1. _test_ Python code with `pytest`
     ```sh
     % uv run pytest
     ```
     or
     ```sh
     % make test
     ```

- or run the above checks in one-shot
  ```sh
  % make --keep-going check
  ```
  `--keep-going` will continue to run checks, even if previous `make` rule fail. Omit if you want to stop after the first `make` rule fails.

## Docker Development Setup (Alternative)

As an alternative to the local development setup above, you can use Docker containers for a consistent development environment across Mac, Linux, and Windows.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (24.0+)
- [Docker Compose](https://docs.docker.com/compose/install/) (2.0+)
- Google Cloud credentials (same as local setup)

### Quick Start

1. Copy environment template:
   ```bash
   cp .env.docker.example .env
   ```

2. Update `.env` with your credentials path:
   ```bash
   # Edit GOOGLE_APPLICATION_CREDENTIALS_HOST to point to your credentials
   GOOGLE_APPLICATION_CREDENTIALS_HOST=/home/<USERNAME>/.config/gcloud/application_default_credentials.json
   ```

3. Start the application:
   ```bash
   docker compose up
   ```

4. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5000

### Development Workflow

- **Hot reload enabled** - Changes to source files are reflected immediately
- **Run backend checks:**
  ```bash
  docker compose exec backend make lint
  docker compose exec backend make typecheck
  docker compose exec backend make test
  ```
- **Run frontend checks:**
  ```bash
  docker compose exec frontend npm run lint
  docker compose exec frontend npm run test -- --run
  ```
- **View logs:**
  ```bash
  docker compose logs -f backend
  docker compose logs -f frontend
  ```

### Stopping

```bash
docker compose down
```

### Troubleshooting

**Windows/WSL2 Performance:**
- Keep source code inside WSL2 filesystem, not Windows filesystem
- Add `consistency: delegated` to volume mounts if experiencing slow performance

**Permission Issues:**
- Ensure Google credentials file is readable: `chmod 644 <credentials-file>`
- On Linux, ensure your user is in the `docker` group: `sudo usermod -aG docker $USER`

**Port Already in Use:**
- Change ports in `docker-compose.yml` if 5000 or 5173 are taken

## Contributing

We currently have regular project meetups: https://www.meetup.com/codepdx/ . Also check out https://www.codepdx.org/ to find our Discord server.

## Remote server setup

On DO, we:

1. added our ssh public keys
2. install nginx
3. Kent got the tls cert (just ask chatgpt?)
