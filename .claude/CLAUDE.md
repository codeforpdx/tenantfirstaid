Welcome to the Tenant First Aid repository. This file contains the main points for new contributors.

## Repository overview

- **Source code**: see [Architecture.md](../Architecture.md) for code organization
- **Tests**: see [Architecture.md](../Architecture.md) for test organization and [README.md](../README.md) for backend quality check flows/commands; see `frontend-builds` job in [pr-checks](../.github/workflows/pr-check.yml) for frontend commands
- **Documentation**: see [Architecture.md](../Architecture.md) for architectural documentation
- **Utilities**: developer commands are defined in the `Makefile`.
- **PR template**: [pull_request_template.md](../.github/pull_request_template.md) describes the information every PR must include.

## Local `./backend` workflow

1. Format, lint and type‑check your changes:

   ```bash
   make fmt
   make lint
   make typecheck
   ```

2. Run the tests:

   ```bash
   make test
   ```

   To run a single test, use `uv run pytest -s -k <test_name>`.

3. Coverage can be generated with (optional but recommended for code changes):
   ```bash
   make test TEST_OPTIONS="--cov tenantfirstaid --cov-report html --cov-branch"
   ```

All python commands should be run via `uv run python ...`

## LangChain Agent Architecture

The backend uses LangChain 1.0.8+ for agent-based conversation management with Vertex AI integration.

### Key Components
- **LangChainChatManager**: Main agent orchestration class (`backend/tenantfirstaid/langchain_chat_manager.py`)
- **retrieve_city_state_laws**: Tool for city/state-specific legal retrieval
- **ChatVertexAI**: LangChain wrapper for Google Gemini

### Environment Variables
```bash
MODEL_NAME=gemini-2.5-pro                          # LLM model name
VERTEX_AI_DATASTORE=projects/.../datastores/...    # RAG corpus ID
SHOW_MODEL_THINKING=false                          # Enable Gemini thinking mode
LANGSMITH_API_KEY=...                              # Optional: Enable LLM evaluations
```

### Testing LangChain Components
```bash
# Run LangChain-specific tests
uv run pytest -m langchain

# Run with LangSmith tracing (requires API key)
LANGSMITH_TRACING=true LANGCHAIN_TRACING_V2=true uv run pytest -m langchain


# Run evaluations (see docs/EVALUATION.md)
uv run python scripts/run_langsmith_evaluation.py --num-samples 20
```

## Local `./frontend` workflow

1. Format, lint and type‑check your changes:

   ```bash
   npm run lint
   npx run format
   ```

2. Build frontend code
   ```bash
   npm run build
   ```

3. Test frontend code
   ```bash
   npm run test -- --run
   ```

4. Test Coverage can be generated with (optional but recommended for code changes):
   ```bash
   npm run test -- --run --coverage
   ```

## Docker Workflow (Alternative)

As an alternative to running services locally, Docker provides a consistent development environment.

### Starting Docker Environment

```bash
docker compose up
```

### Running Backend Checks in Docker

```bash
# Format, lint, typecheck, test
docker compose exec backend make fmt
docker compose exec backend make lint
docker compose exec backend make typecheck
docker compose exec backend make test

# All checks
docker compose exec backend make --keep-going check
```

### Running Frontend Checks in Docker

```bash
docker compose exec frontend npm run lint
docker compose exec frontend npm run format
docker compose exec frontend npm run test -- --run
docker compose exec frontend npm run test -- --run --coverage
```

### Building Production Images Locally

```bash
# Backend
docker build --build-arg TYPE=deploy -t backend:prod ./backend

# Frontend
docker build --build-arg TYPE=deploy -t frontend:prod ./frontend
```

### Notes

- GitHub Actions automatically builds and pushes multi-arch images on push to main
- Use `docker compose down` to stop services
- Use `docker compose down -v` to also remove volumes

## Style notes

- Write comments as full sentences and end them with a period.

## Pull request expectations

PRs should use the template located at [pull_request_template.md](../.github/pull_request_template.md). Provide a summary, test plan and issue number if applicable, then check that:

- for frontend, backend and backend/scripts
  - New tests are added when needed.
  - Documentation is updated.
  - `make lint` and `make format` have been run.
  - The full test suite passes.

## Commit Messages

Commit messages should be concise and written in the imperative mood. Small, focused commits are preferred.

Write commit messages and PR descriptions as a humble but experienced engineer would. Keep it casual, avoid listicles, briefly describe what we're doing and highlight non-obvious implementation choices but don't overthink it.

Don't embarrass me with robot speak, marketing buzzwords, or vague fluff. Just leave a meaningful trace so someone can understand the choices later. Assume the reader is able to follow the code perfectly fine.

## What reviewers look for

- Tests covering new behaviour.
- Consistent style: code formatted with `uv run ruff format`, imports sorted, and type hints passing `make typecheck`.
- Clear documentation for any public API changes.
- Clean history and a helpful PR description.
