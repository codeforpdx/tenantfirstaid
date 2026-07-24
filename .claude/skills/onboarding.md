# Onboarding

Help a new contributor get the repo set up and running locally for the first time.

## Prerequisites

### GitHub account + commit signing

- Join the [Code PDX Contributor team](https://www.codepdx.org/volunteer) (step 2: Connect on Discord & Request Access). You'll receive a GitHub invitation email — accept it.
- Enable [commit signing](https://docs.github.com/authentication/managing-commit-signature-verification) in your GitHub account settings (SSH and GPG keys). GPG is typical.

### uv (Python package manager)

Used by the backend for dependencies and running tools.

```sh
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh
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

### Option A: Docker (simpler)

Requires Docker Desktop or Docker Engine.

```sh
# 1. Copy the root-level compose env file
cp .env.example .env

# 2. Set GCP_CREDENTIALS_FILE to your credentials JSON path
#    (this bind-mounts the file into the container — it is NOT the app env var)
#    Edit .env and set:
#    GCP_CREDENTIALS_FILE=/home/you/.config/gcloud/application_default_credentials.json

# 3. Copy and fill in the backend env file
cp backend/.env.example backend/.env
#    Set LANGSMITH_API_KEY in backend/.env

# 4. Start both services
docker compose up --build
```

- Backend runs on http://localhost:5001
- Frontend runs on http://localhost:5173

Override build targets (e.g. to run CI checks in Docker):

```sh
RUNTIME_TARGET=ci FRONTEND_TARGET=ci docker compose up --build
```

Stop:

```sh
docker compose down
```

### Option B: Native (uv + npm)

```sh
# Backend
cd backend
cp .env.example .env
# Fill in GOOGLE_APPLICATION_CREDENTIALS and LANGSMITH_API_KEY in .env
uv sync
uv run python -m tenantfirstaid.app

# Frontend (new terminal)
cd frontend
npm install
npm run generate-types
npm run dev
```

Open http://localhost:5173 and start chatting.

---

## Getting help

- Discord: #tenantfirstaid-general in the [Code PDX server](https://www.codepdx.org/)
- Meetups: https://www.meetup.com/codepdx/
