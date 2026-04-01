# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

Tenant First Aid is a chatbot for Oregon housing/eviction legal information. Flask backend + React frontend monorepo, deployed on Digital Ocean.

- **Architecture docs**: [Architecture.md](../Architecture.md) — RAG pipeline, endpoints, session management, frontend structure
- **Deployment docs**: [Deployment.md](../Deployment.md) — CI/CD, secrets, infrastructure
- **PR template**: [.github/pull_request_template.md](../.github/pull_request_template.md)
- **Dev commands**: `backend/Makefile`

### Key architecture

- **Backend** (`backend/`): Flask API with LangChain agent orchestration. The agent uses Vertex AI RAG to retrieve Oregon housing law documents and Google Gemini as the LLM. Key files: `langchain_chat_manager.py` (agent orchestration), `langchain_tools.py` (RAG retriever + letter tools), `schema.py` (Pydantic response chunk types shared with frontend).
- **Frontend** (`frontend/`): React 19 + TypeScript + Vite + Tailwind CSS 4. Uses `@langchain/core` message types (`HumanMessage`/`AIMessage`) directly for chat state. Streaming via native `ReadableStream`.
- **Type bridge**: Frontend TypeScript types in `src/types/` are auto-generated from backend Pydantic models via `generate-types` and gitignored. Must regenerate before building or type-checking.

## Backend workflow (run from `backend/`)

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

All python commands should be run via `uv run python ...`

### Environment variables

See `backend/.env.example`. Key ones: `MODEL_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_AI_DATASTORE`, `LANGSMITH_API_KEY`.

### LangSmith evaluations

```bash
uv run python scripts/run_langsmith_evaluation.py --num-samples 20
```

See `docs/EVALUATION.md` for details.

## Frontend workflow (run from `frontend/`)

```bash
npm run generate-types    # Required before build/typecheck — generates src/types/models.ts
npm run lint              # Lint (eslint)
npm run format            # Format (prettier)
npm run typecheck         # Type-check (tsc)
npm run build             # Build (auto-generates types first)
npm run test -- --run     # Run tests (vitest)
npm run test -- --run --coverage  # With coverage
```

`generate-types` requires `uv` to be installed (it runs backend Python to emit JSON Schema, piped through `json2ts`).

## Style notes

- Write comments as full sentences and end them with a period.

## Commit messages

Concise, imperative mood, small focused commits. Write like a humble experienced engineer — casual, no listicles, highlight non-obvious choices. No robot speak, marketing buzzwords, or vague fluff.

## Pull request expectations

Use the PR template. For frontend, backend, and backend/scripts changes:
- Add tests when needed
- Update documentation
- Run `make lint` and `make fmt`
- Full test suite passes

## What reviewers look for

- Tests covering new behaviour
- Consistent style: formatted with `ruff format`, imports sorted, type hints passing `make typecheck`
- Clear documentation for public API changes
- Clean history and helpful PR description
- Consistent environment variable declarations across GitHub Actions, `.env.example`, tests, and docs — no orphaned secrets/variables

## GitHub Actions security

Pin third-party actions to commit SHAs:

```yaml
# Good: SHA with version comment
uses: appleboy/scp-action@ff85246acaad7bdce478db94a363cd2bf7c90345 #v1.0.0

# Bad: floating tag
uses: appleboy/scp-action@v1.0.0
```

Exceptions: Astral (uv) actions may use fully qualified semver tags (e.g. `astral-sh/setup-uv@7.3.0`), and immutable tags are allowed.
