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
# Run LangChain-specific tests
uv run pytest -m langchain

# Run with LangSmith tracing (requires API key)
LANGSMITH_TRACING=true LANGCHAIN_TRACING_V2=true uv run pytest -m langchain

# Run evaluations (see backend/evaluate/EVALUATION.md)
uv run python -m evaluate.run_langsmith_evaluation --num-repetitions 20
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

## Commit messages

Concise, imperative mood, small focused commits. Write like a humble experienced engineer — casual, no listicles, highlight non-obvious choices. No robot speak, marketing buzzwords, or vague fluff.

## Pull Request expectations

Use the PR template. For frontend, backend, and backend/scripts changes:
- Add tests when needed
- Update documentation
- Run `make lint` and `make fmt`
- Full test suite passes

### Pull Request reviews

Perform a comprehensive code review of the modified code with the following focus areas:

1. **Code Quality**
   - Consistent style: formatted with `ruff format`, imports sorted, type hints passing `make typecheck`
   - Clean code principles and best practices
   - Suggest improvements to modularity, composition and dependency inversion where appropriate
   - Identify opportunities for refactoring or simplification
   - Check for code duplication and suggest DRY improvements
   - Identify and suggest removal of dead code or redundant logic
   - Proper error handling and edge cases
   - Code readability and maintainability, including type hints where appropriate
   - Prefer strongly typed interfaces and data structures over stringly-typed where possible
   - Consistent environment variable declarations across GitHub Actions, `.env.example`, tests, and docs — no orphaned secrets/variables
2. **Security**
   - Check for potential security vulnerabilities
   - Validate input sanitization
   - Review authentication/authorization logic
   - Ensure secrets are handled securely and not exposed in code or logs
   - Flag obsolete secrets/configuration/environment variables
3. **Performance**
   - Identify potential performance bottlenecks
   - Review database queries for efficiency
   - Check for memory leaks or resource issues
4. **Testing**
   - Verify adequate test coverage
   - Tests covering new behaviour
   - Review test quality and edge cases
   - Check for missing test scenarios
5. **Documentation**
   - Ensure code is properly documented
   - Clear documentation for public API changes
   - Verify README updates for new features
   - Check API documentation accuracy
   - Clean history and helpful PR description

Provide detailed feedback using inline comments for specific issues.
Use top-level comments for general observations or praise.



## GitHub Actions Security

We pin all third-party actions to commit SHAs to prevent supply chain attacks:

```yaml
# Good: SHA with version comment
uses: appleboy/scp-action@ff85246acaad7bdce478db94a363cd2bf7c90345 #v1.0.0

# Bad: floating tag
uses: appleboy/scp-action@v1.0.0
```

Exceptions: Astral (uv) actions may use fully qualified semver tags (e.g. `astral-sh/setup-uv@7.3.0`), and immutable tags are allowed.
