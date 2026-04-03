# Setup & Environment Variables

> **Audience**: backend contributors. If you just want to run `langgraph dev` locally, see [Local Studio](07-local-studio.md) — the setup there is simpler.

## Initial setup

1. Sign up for a free account at https://smith.langchain.com/ (Personal workspace is sufficient for running evaluations).
2. Generate an API key from your account settings.
3. Copy `backend/.env.example` to `backend/.env` and fill in the values:

```bash
cd backend
cp .env.example .env
# Edit .env with your values
```

## Variable reference

| Variable | Required | Example | Description |
|---|---|---|---|
| `MODEL_NAME` | yes | `gemini-2.5-pro` | LLM model name |
| `GOOGLE_CLOUD_PROJECT` | yes | `tenantfirstaid` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | yes | `global` | Vertex AI location |
| `GOOGLE_APPLICATION_CREDENTIALS` | yes | *(see below)* | GCP credentials — file path locally, inline JSON in Cloud |
| `VERTEX_AI_DATASTORE` | yes | `tenantfirstaid-corpora_...` | Vertex AI Search datastore ID |
| `LANGSMITH_API_KEY` | for evals | `lsv2_pt_...` | LangSmith API key (not needed for `langgraph dev` itself) |
| `LANGSMITH_TRACING` | no | `true` | Enable LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | no | `true` | Enable detailed tracing |
| `LANGSMITH_PROJECT` | no | `tenant-first-aid-dev` | LangSmith project name for traces |
| `SHOW_MODEL_THINKING` | no | `false` | Capture Gemini reasoning in responses |

`GOOGLE_APPLICATION_CREDENTIALS` is the **file path** to your GCP credentials JSON, typically `~/.config/gcloud/application_default_credentials.json`. See the project README for how to set up GCP credentials locally.

## LangSmith Cloud deployment

Cloud deployments don't use a `.env` file. Environment variables are configured in the LangSmith UI instead.

**Setting up the GCP credential as a workspace secret** (to avoid exposing it in deployment settings):

1. Go to **LangSmith → Settings → Workspace Secrets**.
2. Create a secret named `GOOGLE_APPLICATION_CREDENTIALS` with the full JSON content of the service account key file (paste the raw JSON, not a file path).
3. Save.

**Configuring the deployment's environment variables:**

1. Go to **Deployments → your deployment → Settings → Environment Variables**.
2. Add the standard variables:

   | Key | Value |
   |---|---|
   | `MODEL_NAME` | `gemini-2.5-pro` |
   | `GOOGLE_CLOUD_PROJECT` | `tenantfirstaid` |
   | `GOOGLE_CLOUD_LOCATION` | `global` |
   | `VERTEX_AI_DATASTORE` | `tenantfirstaid-corpora_...` |
   | `SHOW_MODEL_THINKING` | `false` |

3. Reference the workspace secret for the credential:

   | Key | Value |
   |---|---|
   | `GOOGLE_APPLICATION_CREDENTIALS` | `{{GOOGLE_APPLICATION_CREDENTIALS}}` |

   The `{{...}}` syntax tells LangSmith to resolve the value from the workspace secret at runtime. Rotating the credential only requires updating the workspace secret — no redeployment needed.

4. Save and redeploy.

`LANGSMITH_API_KEY` is **not** needed in the deployment environment — the Cloud runtime provides it automatically.

---

**Next**: [Dataset Management (CLI)](13-dataset-management.md)
