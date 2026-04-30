# Evaluation Quickstart

## Prerequisites

Make sure you have these installed:
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- [`gcloud` CLI](https://cloud.google.com/sdk/docs/install) — Google Cloud

## 1. Set up Google Cloud credentials

Open your terminal, paste each command below and hit Enter:

```bash
gcloud auth application-default login
```

This opens a browser window — sign in with your Google account. Once done, paste this next:

```bash
gcloud auth application-default set-quota-project tenantfirstaid
```

## 2. Get a LangSmith API key

1. Sign up at https://smith.langchain.com
2. Go to **Settings → API Keys → Create API Key**
3. Copy the key — you'll need it in the next step

## 3. Set up your `.env`

Paste this into your terminal and hit Enter:

```bash
cd backend && cp .env.example .env
```

Then open the `.env` file in a text editor and fill in these values:

| Variable | Value |
|---|---|
| `LANGSMITH_API_KEY` | the key you copied in step 2 |
| `LANGSMITH_TRACING` | `true` |
| `LANGCHAIN_TRACING_V2` | `true` |
| `LANGSMITH_PROJECT` | `tenantfirstaid-dev` |
| `GOOGLE_CLOUD_PROJECT` | `tenantfirstaid` |
| `GOOGLE_CLOUD_LOCATION` | `global` |
| `GOOGLE_APPLICATION_CREDENTIALS` | `~/.config/gcloud/application_default_credentials.json` |
| `VERTEX_AI_DATASTORE_LAWS` | your Vertex AI Search datastore ID (ask a teammate if unsure) |
| `MODEL_NAME` | `gemini-2.5-pro` |

## 4. Push the dataset to LangSmith (one-time)

Paste this into your terminal and hit Enter:

```bash
cd backend && uv run python -m evaluate.langsmith_dataset dataset push evaluate/dataset-tenant-legal-qa-examples.jsonl tenant-legal-qa-scenarios
```

You only need to do this once, or again if the dataset changes.

## 5. Run the evaluation

Paste this into your terminal and hit Enter:

```bash
cd backend && export $(grep -v '^#' .env | xargs) && uv run python -m evaluate.run_langsmith_evaluation
```

This loads your settings and runs the evaluation. It takes roughly 5–15 minutes. Results are printed to the terminal when finished, and also saved to LangSmith so you can view them in the browser.

To run each example more times for more reliable results (takes longer), add `--num-repetitions`:

```bash
cd backend && export $(grep -v '^#' .env | xargs) && uv run python -m evaluate.run_langsmith_evaluation --num-repetitions 20
```

## 6. View results

When the evaluation finishes, the terminal prints a link directly to your results. You can also find them at https://smith.langchain.com → your project → **Experiments tab**.

Each experiment shows per-example scores for legal correctness and tone, with the judge's written rationale for each score. You can compare two experiments side-by-side to measure the impact of a code or prompt change.

## Iterating on the system prompt

To test a prompt change, edit `backend/tenantfirstaid/system_prompt.md` in any text editor, then re-run step 5. Each run creates a new experiment in LangSmith so you can compare scores before and after your change.

## Troubleshooting

**"Dataset not found"** — the dataset hasn't been pushed yet. Re-run step 4.

**"Could not resolve project using application default credentials"** — your Google Cloud credentials aren't loaded. Re-run step 5 — the `export ...` part at the beginning loads them from your `.env` file. If that still fails, re-run step 1.
