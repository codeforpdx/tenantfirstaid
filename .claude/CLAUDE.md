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
