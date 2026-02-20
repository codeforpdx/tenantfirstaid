# Tenant First Aid

A chatbot that provides legal information related to housing and eviction in Oregon.

Live at https://tenantfirstaid.com/

## Local Development

[![PR Checks](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/pr-check.yml)
[![CI-CD (Production)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.production.yml/badge.svg)](https://github.com/codeforpdx/tenantfirstaid/actions/workflows/deploy.production.yml)

### Prerequisites

<details>
<summary>GitHub account</summary>

- You will need a GitHub account (free) to contribute to the project.  No account is necessary to browse the source code.
  - You will be invited to join the [Contributor](https://github.com/orgs/codeforpdx/teams/contributor) team after you complete [step 2 ("Connect on Discord & Request Access") of the Code PDX onboarding](https://www.codepdx.org/volunteer)
  - Look for the invitation email and click the link in the email to accept the invitation.
  - You will also have to enable [commit signing](https://docs.github.com/authentication/managing-commit-signature-verification) by adding a key (typically `GPG`) to your GitHub account (click on your avatar -> Settings -> SSH and GPG keys).
</details>

<details>
<summary>Astral UV</summary>

- `uv` is used in the *backend* to install/manage Python dependencies and run Python sub-tools (e.g. `pytest`)
[Install uv](https://docs.astral.sh/uv/getting-started/installation/)
</details>

<details>
<summary>Google Cloud application default credentials file</summary>

- This is needed to spin up a local instance of the backend (i.e. API calls to the chat LLM and RAG agent).
- The chatbot now uses Google Gemini (previously OpenAI's ChatGPT).
- The `tenantfirstaid` Google project admin will need to manually assign a role to you (gmail account).  Reach out in the Discord channel #[tenantfirstaid-general](https://discord.com/channels/1068260532806766733/1367177752792531115) to arrange this.
- You need to authenticate with the gcloud cli to develop, following these instructions:
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

### Updating the RAG Corpus

The Vertex AI Search datastore is populated from per-section entries generated from the source legal documents in `backend/scripts/documents/`. A pre-built `corpus.jsonl` is committed to the repo, so you only need to run these steps if source documents change.

1. Regenerate the corpus:
   ```sh
   uv run python scripts/create_corpus_jsonl.py
   ```
2. Upload to Vertex AI Search (requires GCP credentials):
   ```sh
   uv run python scripts/ingest_corpus.py
   ```

`ingest_corpus.py` makes incremental updates so existing documents are updated in place.

**Note:** `create_corpus_jsonl.py` uses a document-specific parser for each source file (ORS, OAR, PCC, EHC) based on each format's section header pattern. If you add a new source document, check whether an existing parser covers its format — if not, a new parser will need to be added to the script before the section splitting will work correctly.

## Contributing

We currently have regular project meetups: https://www.meetup.com/codepdx/ . Also check out https://www.codepdx.org/ to find our Discord server.

## Remote server setup

On DO, we:

1. added our ssh public keys
2. install nginx
3. Kent got the tls cert (just ask chatgpt?)
