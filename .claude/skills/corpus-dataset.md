# Corpus Dataset

Reference for adding or modifying law documents in `backend/scripts/documents/`.

## ASCII requirement

All `.txt` files must be **pure ASCII**. Vertex AI RAG ingestion has produced mojibake when UTF-8 is present. Before committing any `.txt` file, verify:

```bash
LC_ALL=C grep -n '[^[:print:][:space:]]' path/to/file.txt  # must produce no output
```

`make enforce-ascii` walks the tree and applies known replacements in place. `make generate-metadata` runs the same pass before building `metadata.jsonl`. Both warn with a suggested replacement for any character they cannot handle. For CI-friendly validation without rewriting, run `make enforce-ascii ASCII_OPTIONS=--check`.

### Common replacements

| Character | Unicode | Replace with |
|---|---|---|
| `'` | U+2019 right single quote | `'` |
| `"` `"` | U+201C/U+201D double quotes | `"` |
| `§` | U+00A7 section sign | `Section ` |
| `§§` | U+00A7 U+00A7 | `Sections ` |
| `—` | U+2014 em dash | `--` |
| `–` | U+2013 en dash | `-` |
| `•` | U+2022 bullet | `-` |

See `ASCII_REPLACEMENTS` in `backend/scripts/enforce_ascii.py` for the full list.

## RAG ingestion pipeline (`backend/scripts/`)

The RAG datastore is rebuilt by uploading the documents tree and a generated `metadata.jsonl` to a fresh GCS bucket, then creating a new Vertex AI Search datastore and Search app from that bucket. The steps are split so each is independently runnable:

```bash
# 1. (Optional) Validate ASCII without touching files; useful in CI.
make enforce-ascii ASCII_OPTIONS=--check

# 2. Generate metadata.jsonl. Runs ASCII enforcement as a side effect.
make generate-metadata GCS_BUCKET_NAME=my-bucket

# 3. Create a new GCS bucket (fails if it already exists) and upload everything
#    referenced by metadata.jsonl, plus metadata.jsonl itself.
make upload-to-gcs GCS_BUCKET_NAME=my-bucket
make upload-to-gcs GCS_BUCKET_NAME=my-bucket LOCATION=us-central1
make upload-to-gcs GCS_BUCKET_NAME=my-bucket UPLOAD_OPTIONS=--dry-run

# 4. Create a Vertex AI Search datastore and import documents from the bucket.
#    Polls until the import finishes; pass DATASTORE_OPTIONS=--no-wait to skip.
make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds
make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds LOCATION=us
make create-datastore-gcs GCS_BUCKET_NAME=my-bucket DATASTORE_ID=my-ds DATASTORE_OPTIONS=--dry-run

# 5. Create a Vertex AI Search app and link it to the datastore.
#    Pass the same DATASTORE_ID used in step 4. The Search app is for browsing
#    and previewing the datastore in the GCP console; the LangChain retriever
#    used by the backend (VertexAISearchRetriever) reads the datastore directly
#    and does not depend on this app.
make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app
make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app LOCATION=us
make create-app-gcs DATASTORE_ID=my-ds APP_ID=my-app APP_OPTIONS=--dry-run
```

`upload-to-gcs` requires `GOOGLE_APPLICATION_CREDENTIALS` to point at a service account with `storage.buckets.create` and `storage.objects.create` permissions on the target project. `create-datastore-gcs` additionally requires `storage.buckets.get` (for the bucket region compatibility check), `discoveryengine.datastores.create`, and `discoveryengine.documents.import` permissions. `create-app-gcs` additionally requires `discoveryengine.engines.create`. After the app is created, set `VERTEX_AI_DATASTORE_LAWS` in `.env` to the datastore ID.

**Cross-project note:** if the GCS bucket and the Discovery Engine project are in different GCP projects, the Vertex AI Search service agent for the Discovery Engine project must be granted `roles/storage.objectViewer` on the bucket. In same-project setups this is automatic.

## Debugging and diagnosis

Two helper scripts inspect Vertex AI Search directly, bypassing LangChain/LangGraph, so you can isolate retrieval behavior from the agent framework:

```bash
# List the datastores in the project (IDs, display names, document counts).
uv run python -m scripts.vertex_ai_list_datastores

# Query a datastore directly: what passages come back for a query + filter?
uv run python -m scripts.vertex_ai_search search "security deposit interest" --state or
uv run python -m scripts.vertex_ai_search search "ORS 90.155 notice delivery" --state or --city portland
```

Use these to verify a freshly created datastore actually returns the expected documents before pointing the backend at it via `VERTEX_AI_DATASTORE_LAWS`.

## Publication cadence

Oregon publishes statutes and annotations on offset biennial cycles:

- **Statutes** (`ORS*.txt`, `OAR*.txt`) — published in odd years after each long legislative session. [Current edition](https://www.oregonlegislature.gov/bills_laws/pages/ors.aspx).
- **Annotations** (`ORS*_annotations.txt`) — published in the fall of each even-numbered year as a Cumulative Supplement. [Current edition](https://www.oregonlegislature.gov/bills_laws/Pages/Annotations.aspx).

This is why statutes and annotations live in different year subfolders.

## URL patterns

Chapter pages are at predictable URLs (`NNN` = three-digit zero-padded chapter number, lowercase letter suffix for sub-chapters):

- Statutes: `https://www.oregonlegislature.gov/bills_laws/ors/orsNNN.html`
- Annotations: `https://www.oregonlegislature.gov/bills_laws/ors/anoNNN.html`

Examples: chapter 90 → `ors090.html` / `ano090.html`; chapter 659A → `ors659a.html` / `ano659a.html`.
