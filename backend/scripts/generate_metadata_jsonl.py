"""Generate metadata.jsonl for Vertex AI RAG ingestion from the documents directory.

Walks backend/scripts/documents/or/ recursively, infers city/state metadata
from the directory structure, and writes a flat metadata.jsonl file where all
GCS URIs point to the bucket root (files are uploaded flat, not mirrored).

ASCII enforcement runs first via scripts.enforce_ascii so that any non-ASCII
content is rewritten in place (or fails loudly with a suggestion table).

To run:
  make generate-metadata GCS_BUCKET_NAME=<bucket>                                    # all documents
  make generate-metadata GCS_BUCKET_NAME=<bucket> LOC_OPTIONS="--oregon"             # Oregon state only
  make generate-metadata GCS_BUCKET_NAME=<bucket> LOC_OPTIONS="--portland"           # Portland only
  make generate-metadata GCS_BUCKET_NAME=<bucket> LOC_OPTIONS="--oregon --eugene"    # multiple
"""

import argparse
import json
from pathlib import Path

from google.cloud.discoveryengine_v1.types import Document
from google.protobuf.json_format import MessageToDict

from scripts.enforce_ascii import validate_and_rewrite_tree

DOCUMENTS_DIR = Path(__file__).parent / "documents" / "or"
OUTPUT_FILE = DOCUMENTS_DIR / "metadata.jsonl"

CITY_DIRS = {"eugene", "portland"}


def infer_city(path: Path) -> str | None:
    for part in path.parts:
        if part in CITY_DIRS:
            return part
    return None


def _in_scope(city: str | None, scopes: set[str]) -> bool:
    """Return True if the file's inferred city is in one of the requested scopes (or scopes is empty)."""
    if not scopes:
        return True
    scope = "or" if city is None else city
    return scope in scopes


def build_entries(documents_dir: Path, bucket: str, scopes: set[str]) -> list[Document]:
    def in_scope(path: Path) -> bool:
        return _in_scope(infer_city(path.relative_to(documents_dir)), scopes)

    validate_and_rewrite_tree(documents_dir, file_filter=in_scope)

    entries: list[Document] = []
    seen_ids: set[str] = set()

    for txt_file in sorted(documents_dir.rglob("*.txt")):
        city = infer_city(txt_file.relative_to(documents_dir))
        if not _in_scope(city, scopes):
            continue

        if txt_file.stem in seen_ids:
            raise RuntimeError(
                f"Duplicate document id '{txt_file.stem}': two .txt files share the same basename. "
                "Files are uploaded flat to GCS, so one would overwrite the other."
            )
        seen_ids.add(txt_file.stem)

        entries.append(
            Document(
                id=txt_file.stem,
                # State-level docs use the literal string "null" (not JSON null,
                # which Vertex drops on import) so the retriever's city: ANY("null")
                # filter matches them.
                struct_data={
                    "city": city if city is not None else "null",
                    "state": "or",
                },
                content=Document.Content(
                    mime_type="text/plain",
                    uri=f"gs://{bucket}/{txt_file.name}",
                ),
            )
        )

    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket name to use in metadata URIs (e.g. my-rag-bucket).",
    )
    parser.add_argument(
        "--oregon",
        dest="include_or",
        action="store_true",
        help="Include Oregon state documents.",
    )
    parser.add_argument(
        "--portland",
        dest="include_portland",
        action="store_true",
        help="Include Portland documents.",
    )
    parser.add_argument(
        "--eugene",
        dest="include_eugene",
        action="store_true",
        help="Include Eugene documents.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bucket = args.bucket
    scopes: set[str] = set()
    if args.include_or:
        scopes.add("or")
    if args.include_portland:
        scopes.add("portland")
    if args.include_eugene:
        scopes.add("eugene")

    entries = build_entries(DOCUMENTS_DIR, bucket, scopes)

    with OUTPUT_FILE.open("w") as f:
        for entry in entries:
            f.write(json.dumps(MessageToDict(Document.pb(entry))) + "\n")
            print(f"  {entry.id} -> {entry.content.uri}")

    print(f"Wrote {len(entries)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
