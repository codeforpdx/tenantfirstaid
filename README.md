# Tenant First Aid

A chatbot that provides legal advice related to housing and eviction

Live at https://tenantfirstaid.com/

## Local Development

[![PR Checks](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml)
[![CI-CD](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.yml)

### Prerequisites
 - [uv](https://docs.astral.sh/uv/getting-started/installation/)
 - [docker](https://www.docker.com/)

1. copy `backend/.env.example` to a new file named `.env` in the same directory. The chatbot now uses Google Gemini instead of OpenAI.
1. `cd backend`
1. `docker-compose up` (use `-d` if you want to run this in the background, otherwise open a new terminal)
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
    1. *format* Python code with `ruff`
       ```sh
       % uv run ruff format
       ```
       or
       ```sh
       % make fmt
       ```
    1. *lint* Python code with `ruff`
       ```sh
       % uv run ruff check
       ```
       or
       ```sh
       % make lint
       ```
    1. *typecheck* Python code with `ty`
       ```sh
       % uv run ty check
       ```
       or
       ```sh
       % make typecheck
       ```

       *typecheck* with other Python typecheckers which are not protected in [PR Checks](.github/workflows/pr-check.yml) - useful for completeness & a 2nd opinion
       1. *typecheck* Python code with `mypy`
          ```sh
          % uv run mypy -p tenantfirstaid --python-executable .venv/bin/python3 --check-untyped-defs
          ```
          or
          ```sh
          % make typecheck-mypy
          ```
       1. *typecheck* Python code with `pyrefly`
          ```sh
          % uv run pyrefly check --python-interpreter .venv/bin/python3
          ```
          or
          ```sh
          % make typecheck-pyrefly
          ```
    1. *test* Python code with `pytest`
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
    `--keep-going` will continue to run checks, even if previous `make` rule fail.  Omit if you want to stop after the first `make` rule fails.

## Versioning and Releases

This project uses [semantic versioning](https://semver.org/) with automated version management via `setuptools-scm`. The version is automatically derived from Git tags.

### Creating a Release

1. **Determine the version bump type:**
   - **Patch release** (0.2.0 → 0.2.1): Bug fixes, minor improvements
   - **Minor release** (0.2.0 → 0.3.0): New features, backward-compatible changes
   - **Major release** (0.2.0 → 1.0.0): Breaking changes

2. **Create and push a tag:**
   ```bash
   # For a patch release (default for regular PRs)
   git tag v0.2.1
   git push origin v0.2.1
   
   # For a minor release (feature additions)
   git tag v0.3.0
   git push origin v0.3.0
   
   # For a major release (breaking changes)
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **The version will automatically be updated** in the backend API and displayed in the frontend UI.

### Checking the Current Version

- **Backend API**: Visit `/api/version` endpoint
- **Frontend UI**: Check the sidebar navigation (bottom)
- **Command line**: Run `uv run python -c "from importlib.metadata import version; print(version('tenant-first-aid'))"`

## Contributing

We currently have regular project meetups: https://www.meetup.com/codepdx/ . Also check out https://www.codepdx.org/ to find our Discord server.

## Remote server setup
On DO, we:
1. added our ssh public keys
2. install nginx
3. Kent got the tls cert (just ask chatgpt?)