"""Upload the per-section corpus to Vertex AI Search.

Reads corpus.jsonl (produced by create_corpus_jsonl.py) and imports each
section as a separate document into the configured Vertex AI Search datastore.
Structured metadata (city, state, title) is stored alongside the raw section
text so the retriever's city/state filters keep working.

Documents are imported in batches of 100 (the API's recommended maximum for
inline imports).  Each import uses INCREMENTAL reconciliation, so re-running
the script is safe — existing documents are updated in place.

Usage:
    uv run python scripts/ingest_corpus.py [--corpus PATH] [--dry-run]

Prerequisites:
    - .env (or environment) must have all variables required by _GoogEnvAndPolicy
    - The datastore must already exist in Vertex AI Search
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1beta
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

# Allow running from the repo root or from within backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from tenantfirstaid.constants import SINGLETON  # noqa: E402

DOCUMENTS_DIR = Path(__file__).parent / "documents"
DEFAULT_CORPUS = DOCUMENTS_DIR / "corpus.jsonl"
BATCH_SIZE = 100

# RFC-1034 allows only letters, digits, and hyphens; max 63 chars.
_ID_UNSAFE = re.compile(r"[^a-zA-Z0-9-]")


def _safe_doc_id(raw_id: str) -> str:
    """Convert a corpus section id to an RFC-1034-compliant document id."""
    sanitized = _ID_UNSAFE.sub("-", raw_id)
    if len(sanitized) > 63:
        # Append an 8-char hash so truncated IDs stay unique.
        suffix = "-" + hashlib.sha1(raw_id.encode()).hexdigest()[:8]
        sanitized = sanitized[: 63 - len(suffix)] + suffix
    return sanitized


def _load_credentials() -> Credentials | service_account.Credentials:
    if SINGLETON.GOOGLE_APPLICATION_CREDENTIALS is None:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set")

    cred_path = Path(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)
    with cred_path.open("r") as f:
        cred_type = json.load(f).get("type")

    if cred_type == "authorized_user":
        return Credentials.from_authorized_user_file(
            SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
        )
    if cred_type == "service_account":
        return service_account.Credentials.from_service_account_file(
            SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
        )
    raise ValueError(f"Unknown credential type: {cred_type!r}")


def _make_client(
    credentials: Credentials | service_account.Credentials,
) -> discoveryengine_v1beta.DocumentServiceClient:
    location = SINGLETON.GOOGLE_CLOUD_LOCATION or "global"
    options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    return discoveryengine_v1beta.DocumentServiceClient(
        credentials=credentials,
        client_options=options,
    )


def _build_document(section: dict) -> discoveryengine_v1beta.Document:
    """Convert one corpus entry to a Discovery Engine Document."""
    return discoveryengine_v1beta.Document(
        id=_safe_doc_id(section["id"]),
        # Structured metadata used by the city/state retrieval filters.
        json_data=json.dumps(
            {
                "title": section.get("title", ""),
                # "null" is the sentinel used by __filter_builder in langchain_tools.py
                # when no city is specified (i.e. state-level statutes).
                "city": section.get("city", "null"),
                "state": section.get("state", "or"),
            },
            ensure_ascii=False,
        ),
        # Raw statute text for extractive answers / chunk retrieval.
        content=discoveryengine_v1beta.Document.Content(
            raw_bytes=section["content"].encode("utf-8"),
            mime_type="text/plain",
        ),
    )


def _import_batch(
    client: discoveryengine_v1beta.DocumentServiceClient,
    parent: str,
    batch: list[discoveryengine_v1beta.Document],
) -> None:
    request = discoveryengine_v1beta.ImportDocumentsRequest(
        parent=parent,
        inline_source=discoveryengine_v1beta.ImportDocumentsRequest.InlineSource(
            documents=batch,
        ),
        reconciliation_mode=(
            discoveryengine_v1beta.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
        ),
    )
    operation = client.import_documents(request)
    result = operation.result(timeout=300)
    if result.error_samples:
        for err in result.error_samples:
            print(f"  [error] {err}", file=sys.stderr)


def run(corpus_path: Path, dry_run: bool) -> None:
    sections = []
    with corpus_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                sections.append(json.loads(line))

    print(f"Loaded {len(sections)} sections from {corpus_path}")

    if dry_run:
        print(
            f"[dry-run] would import {len(sections)} documents in "
            f"{-(-len(sections) // BATCH_SIZE)} batch(es)"
        )
        return

    credentials = _load_credentials()
    client = _make_client(credentials)

    if SINGLETON.GOOGLE_CLOUD_PROJECT is None:
        raise ValueError("GOOGLE_CLOUD_PROJECT is not set")
    if SINGLETON.VERTEX_AI_DATASTORE is None:
        raise ValueError("VERTEX_AI_DATASTORE is not set")

    parent = client.branch_path(
        project=SINGLETON.GOOGLE_CLOUD_PROJECT,
        location=SINGLETON.GOOGLE_CLOUD_LOCATION or "global",
        data_store=SINGLETON.VERTEX_AI_DATASTORE,
        branch="0",
    )
    print(f"Target: {parent}")

    batches = [
        sections[i : i + BATCH_SIZE] for i in range(0, len(sections), BATCH_SIZE)
    ]
    for n, batch in enumerate(batches, start=1):
        docs = [_build_document(s) for s in batch]
        print(
            f"Importing batch {n}/{len(batches)} ({len(docs)} documents)...",
            end=" ",
            flush=True,
        )
        _import_batch(client, parent, docs)
        print("done")

    print(f"\nImported {len(sections)} documents.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="Path to corpus.jsonl (default: scripts/documents/corpus.jsonl)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run(args.corpus, args.dry_run)
