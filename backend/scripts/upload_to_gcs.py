"""Create a fresh GCS bucket and upload law documents + metadata.jsonl.

Refuses to reuse an existing bucket so each RAG ingestion has a clean,
dedicated bucket. Run via `make upload-to-gcs`.
"""

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage
from google.cloud.discoveryengine_v1.types import Document
from google.protobuf.json_format import ParseError

from scripts.enforce_ascii import validate_and_rewrite_tree
from tenantfirstaid.constants import SINGLETON
from tenantfirstaid.google_auth import load_gcp_credentials

DOCUMENTS_DIR = Path(__file__).parent / "documents" / "or"
DEFAULT_METADATA_FILE = DOCUMENTS_DIR / "metadata.jsonl"
# GCS bucket locations are uppercase (US, EU, ASIA), unlike the lowercase Vertex
# AI Search multi-regions (us, eu, global). This US bucket pairs with a "us"
# datastore; see check_bucket_location_compat in create_datastore_gcs.py.
DEFAULT_BUCKET_LOCATION = "US"


class UploadError(RuntimeError):
    """Raised when the upload pipeline cannot proceed."""


def _iter_documents(metadata_path: Path) -> Iterator[Document]:
    # ParseError covers both bad JSON and schema mismatches.
    with metadata_path.open() as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield cast(Document, Document.from_json(line))
            except ParseError as e:
                raise UploadError(f"{metadata_path}:{i}: {e}") from e


def _uri_to_filename(uri: str, expected_bucket: str) -> str:
    """Parse a gs:// URI, verifying it points at the expected bucket.

    Returns the object name (which is the .txt filename, since uploads are flat).
    """
    parsed = urlparse(uri)
    if parsed.scheme != "gs":
        raise UploadError(f"URI {uri!r} is not a gs:// URI.")
    if parsed.netloc != expected_bucket:
        raise UploadError(
            f"URI {uri!r} points at bucket {parsed.netloc!r}, "
            f"but --bucket is {expected_bucket!r}. "
            "Re-run generate-metadata with the new bucket name."
        )
    name = parsed.path.lstrip("/")
    if not name:
        raise UploadError(f"URI {uri!r} has no object name.")
    if "/" in name:
        raise UploadError(
            f"URI {uri!r} has a subpath; uploads are flat -- "
            "metadata.jsonl URIs must be of the form gs://<bucket>/<filename>."
        )
    return name


def _resolve_local_files(
    documents_dir: Path, expected_names: set[str]
) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for txt_file in documents_dir.rglob("*.txt"):
        if txt_file.name in expected_names:
            if txt_file.name in resolved:
                raise UploadError(
                    f"Duplicate file {txt_file.name!r} under {documents_dir}: "
                    f"both {resolved[txt_file.name]} and {txt_file}."
                )
            resolved[txt_file.name] = txt_file

    missing = expected_names - resolved.keys()
    if missing:
        raise UploadError(
            f"metadata.jsonl references files not found under {documents_dir}: "
            + ", ".join(sorted(missing))
        )
    return resolved


def plan_upload(
    bucket: str, metadata_path: Path, documents_dir: Path
) -> tuple[dict[str, Path], Path]:
    if not metadata_path.exists():
        raise UploadError(
            f"metadata.jsonl not found at {metadata_path}. "
            f"Run `make generate-metadata GCS_BUCKET_NAME={bucket}` first."
        )

    expected_names: set[str] = set()
    for doc in _iter_documents(metadata_path):
        if not doc.content.uri:
            raise UploadError(f"metadata entry missing content.uri: id={doc.id!r}")
        expected_names.add(_uri_to_filename(doc.content.uri, bucket))

    name_to_path = _resolve_local_files(documents_dir, expected_names)
    return name_to_path, metadata_path


def create_bucket(client: storage.Client, name: str, location: str) -> storage.Bucket:
    try:
        return client.create_bucket(name, location=location)
    except gcp_exceptions.Conflict as e:
        raise UploadError(
            f"Bucket {name!r} already exists. "
            "Pick a different bucket name or delete the existing bucket first."
        ) from e


def upload_files(
    bucket_obj: storage.Bucket,
    name_to_path: dict[str, Path],
    metadata_path: Path,
) -> None:
    for object_name in sorted(name_to_path):
        local_path = name_to_path[object_name]
        blob = bucket_obj.blob(object_name)
        blob.upload_from_filename(str(local_path), content_type="text/plain")
        print(f"  uploaded {object_name} ({local_path})")

    metadata_blob = bucket_obj.blob(metadata_path.name)
    metadata_blob.upload_from_filename(
        str(metadata_path), content_type="application/jsonl"
    )
    print(f"  uploaded {metadata_path.name} ({metadata_path})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket name to create. Must not already exist.",
    )
    parser.add_argument(
        "--location",
        default=DEFAULT_BUCKET_LOCATION,
        help=f"GCS bucket location (default: {DEFAULT_BUCKET_LOCATION}). "
        "Use a multi-region (US, EU, ASIA) or single-region (us-central1, etc.).",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA_FILE,
        help=f"Path to metadata.jsonl (default: {DEFAULT_METADATA_FILE}).",
    )
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=DOCUMENTS_DIR,
        help=f"Root of documents tree (default: {DOCUMENTS_DIR}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve files and validate, but do not call GCS or create the bucket.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    validate_and_rewrite_tree(args.documents_dir, check_only=True)

    name_to_path, metadata_path = plan_upload(
        args.bucket, args.metadata, args.documents_dir
    )

    print(
        f"Planned upload: {len(name_to_path)} document(s) + metadata.jsonl "
        f"-> gs://{args.bucket}/ (location: {args.location})"
    )

    if args.dry_run:
        for name in sorted(name_to_path):
            print(f"  [dry-run] would upload {name} from {name_to_path[name]}")
        print(f"  [dry-run] would upload {metadata_path.name} from {metadata_path}")
        return

    credentials = load_gcp_credentials(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)
    client = storage.Client(
        credentials=credentials, project=SINGLETON.GOOGLE_CLOUD_PROJECT
    )
    bucket_obj = create_bucket(client, args.bucket, args.location)
    print(f"Created bucket gs://{args.bucket} in {args.location}.")

    upload_files(bucket_obj, name_to_path, metadata_path)
    print(f"Done. {len(name_to_path) + 1} object(s) uploaded to gs://{args.bucket}.")


if __name__ == "__main__":
    try:
        main()
    except UploadError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
