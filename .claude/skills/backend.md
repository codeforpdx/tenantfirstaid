# Backend

Reference for backend development workflow. Run all commands from `backend/`.

## Commands

```bash
make fmt                  # Format + sort imports (ruff)
make lint                 # Lint (ruff)
make typecheck            # Type-check (ty)
make test                 # Run tests (pytest)
make --keep-going check   # All of the above in one shot

# Single test
uv run pytest -s -k <test_name>

# LangChain-specific tests
uv run pytest -m langchain

# Coverage
make test TEST_OPTIONS="--cov tenantfirstaid --cov-report html --cov-branch"
```

All Python commands must be run via `uv run python ...`. Use the `/uv` skill for uv-specific guidance.

## Environment variables

See `backend/.env.example`. Key ones:

| Variable | Description |
|---|---|
| `MODEL_NAME` | LLM model name (e.g. `gemini-2.5-pro`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP credentials JSON |
| `VERTEX_AI_DATASTORE_LAWS` | Vertex AI Search datastore ID for the laws corpus |
| `LANGSMITH_API_KEY` | LangSmith API key (required for evaluations) |
| `LANGSMITH_TRACING` | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | Set to `true` for detailed tracing |
| `LANGSMITH_PROJECT` | LangSmith project name for traces |

## LangSmith evaluations

```bash
# Run LangChain-specific tests
uv run pytest -m langchain

# Run with LangSmith tracing
LANGSMITH_TRACING=true LANGCHAIN_TRACING_V2=true uv run pytest -m langchain

# Run full evaluation suite
uv run run-langsmith-evaluation --num-repetitions 20
```

See `/evaluation` for the full evaluation workflow.

## Docker

Backend Dockerfile targets (`backend/Dockerfile`):

| Target | Purpose |
|---|---|
| `runtime` | Production image (gunicorn, no dev deps) |
| `ci` | Full dev environment for running checks |

Build a specific target:

```sh
docker build -f backend/Dockerfile --target runtime -t tenantfirstaid-backend:runtime backend
```

Run checks via compose:

```sh
RUNTIME_TARGET=ci docker compose run backend uv run --dev pytest -q
```
