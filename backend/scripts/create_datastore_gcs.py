"""Create a Vertex AI Search datastore and import documents from a GCS bucket.

Companion to scripts.upload_to_gcs. Creates an unstructured, search-only
datastore configured for GCS ingestion and triggers an import from
gs://<bucket>/metadata.jsonl. Polls until the import finishes unless
--no-wait is passed. Run via `make create-datastore-gcs`.
"""

import argparse
import sys
from typing import cast

from google.api_core import exceptions as gcp_exceptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage

from scripts.shared import collection_path, datastore_path, validate_resource_name
from tenantfirstaid.constants import DEFAULT_VERTEX_AI_SEARCH_LOCATION, SINGLETON
from tenantfirstaid.google_auth import (
    discoveryengine_client_options,
    load_gcp_credentials,
)

METADATA_OBJECT_NAME = "metadata.jsonl"
# Upper bound for the rollback delete-datastore LRO. If the same conditions
# that broke import (auth/network) also block the delete, this lets us surface
# a clear "manual cleanup required" message instead of hanging.
ROLLBACK_TIMEOUT_SECONDS = 120
# The Discovery Engine document schema for metadata.jsonl entries that are full
# Document protos (produced by generate_metadata_jsonl.py). Other valid values
# are "content" and "custom", but those require different metadata formats.
GCS_DATA_SCHEMA = "document"


class DatastoreError(RuntimeError):
    """Raised when the datastore pipeline cannot proceed."""


def _branch_path(project: str, location: str, datastore_id: str) -> str:
    return f"{datastore_path(project, location, datastore_id)}/branches/default_branch"


def check_bucket_location_compat(
    storage_client: storage.Client,
    bucket_name: str,
    datastore_location: str,
) -> None:
    """Fail early if the bucket's region is incompatible with the datastore location.

    Vertex AI Search 'us' only accepts US-region buckets; 'eu' only accepts
    EU/European-region buckets. 'global' accepts any region.
    """
    bucket = storage_client.get_bucket(bucket_name)
    bucket_location = (bucket.location or "").upper()
    ds_location = datastore_location.lower()

    if ds_location == "us":
        compatible = bucket_location == "US" or bucket_location.startswith("US-")
    elif ds_location == "eu":
        compatible = (
            bucket_location == "EU"
            or bucket_location.startswith("EU-")
            or bucket_location.startswith("EUROPE-")
        )
    else:
        return  # "global" and unrecognized locations carry no regional constraint.

    if not compatible:
        raise DatastoreError(
            f"Bucket {bucket_name!r} is in region {bucket_location!r}, which is "
            f"incompatible with datastore location {datastore_location!r}. "
            "Use a matching region bucket, or pass --location global."
        )


def create_datastore(
    client: discoveryengine.DataStoreServiceClient,
    project: str,
    location: str,
    datastore_id: str,
    display_name: str,
) -> discoveryengine.DataStore:
    """Create an unstructured, search-only datastore. Fails if datastore_id already exists."""
    parent = collection_path(project, location)
    data_store = discoveryengine.DataStore(
        display_name=display_name,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )
    request = discoveryengine.CreateDataStoreRequest(
        parent=parent,
        data_store=data_store,
        data_store_id=datastore_id,
    )
    try:
        operation = client.create_data_store(request=request)
    except gcp_exceptions.AlreadyExists as e:
        raise DatastoreError(
            f"Datastore {datastore_id!r} already exists under {parent}. "
            "Pick a different DATASTORE_ID or delete the existing datastore first (BUT DO NOT DELETE/REPLACE A PRODUCTION DATASTORE!!!)."
        ) from e

    # create_data_store is a fast LRO; waiting keeps the script linear.
    return cast(discoveryengine.DataStore, operation.result())


def import_documents(
    client: discoveryengine.DocumentServiceClient,
    project: str,
    location: str,
    datastore_id: str,
    bucket: str,
    wait: bool,
) -> None:
    """Import documents from gs://<bucket>/metadata.jsonl into datastore_id.

    Uses FULL reconciliation, so the datastore is replaced to exactly mirror
    metadata.jsonl. Callers must guarantee the datastore is freshly created
    (no pre-existing documents) -- this script enforces that by creating the
    datastore in the same run and rolling it back on failure.
    """
    parent = _branch_path(project, location, datastore_id)
    gcs_uri = f"gs://{bucket}/{METADATA_OBJECT_NAME}"
    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[gcs_uri],
            data_schema=GCS_DATA_SCHEMA,
        ),
        # FULL ensures the datastore exactly mirrors metadata.jsonl: any document
        # not in the import is deleted. Safe here because each ingestion creates
        # a fresh datastore, and protects against drift if this is ever re-run.
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL,
    )
    operation = client.import_documents(request=request)
    print(f"Started import: {operation.operation.name}")

    if not wait:
        print("Skipping wait (--no-wait). Check the operation status in the console.")
        return

    print("Waiting for import to finish (this can take several minutes)...")
    response = operation.result()
    metadata = cast(discoveryengine.ImportDocumentsMetadata, operation.metadata)
    print(
        "Import finished. "
        f"success={metadata.success_count} failure={metadata.failure_count}"
    )
    if response.error_samples:
        print(f"First {len(response.error_samples)} error sample(s):")
        for err in response.error_samples:
            print(f"  - {err.message}")


def delete_datastore(
    client: discoveryengine.DataStoreServiceClient,
    datastore_name: str,
    timeout: float = ROLLBACK_TIMEOUT_SECONDS,
) -> None:
    """Delete a datastore by its full resource name. Used for rollback on import failure.

    A finite timeout ensures a stuck delete LRO surfaces as an error caught by
    the caller's "manual cleanup required" path instead of hanging the process.
    """
    request = discoveryengine.DeleteDataStoreRequest(name=datastore_name)
    operation = client.delete_data_store(request=request)
    operation.result(timeout=timeout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket holding metadata.jsonl and the document objects.",
    )
    parser.add_argument(
        "--datastore-id",
        required=True,
        type=validate_resource_name,
        help="Resource ID for the new datastore. Lowercase letters, digits, hyphens; must begin with a letter or digit (1-63 chars). Reuse this same value as --datastore-id for create-app-gcs.",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="Human-readable display name (default: datastore ID).",
    )
    parser.add_argument(
        "--location",
        default=DEFAULT_VERTEX_AI_SEARCH_LOCATION,
        help=(
            f"Vertex AI Search location (default: {DEFAULT_VERTEX_AI_SEARCH_LOCATION}). "
            "Typical values: global, us, eu."
        ),
    )
    parser.add_argument(
        "--no-wait",
        dest="wait",
        action="store_false",
        help="Return as soon as the import is queued instead of polling to completion. "
        "If the import fails asynchronously, the datastore must be manually deleted before re-running.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved plan but do not call the Discovery Engine API.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = SINGLETON.GOOGLE_CLOUD_PROJECT
    display_name = args.display_name or args.datastore_id

    print(
        f"Plan: create datastore {datastore_path(project, args.location, args.datastore_id)!r} "
        f"(display_name={display_name!r}) and import from "
        f"gs://{args.bucket}/{METADATA_OBJECT_NAME}."
    )

    if args.dry_run:
        print("[dry-run] no Discovery Engine API calls made.")
        return

    credentials = load_gcp_credentials(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)

    storage_client = storage.Client(credentials=credentials, project=project)
    check_bucket_location_compat(storage_client, args.bucket, args.location)

    client_options = discoveryengine_client_options(args.location)

    datastore_client = discoveryengine.DataStoreServiceClient(
        credentials=credentials, client_options=client_options
    )
    created = create_datastore(
        datastore_client, project, args.location, args.datastore_id, display_name
    )
    datastore_id = created.name.split("/")[-1]
    print(f"Created datastore: {created.name}")

    document_client = discoveryengine.DocumentServiceClient(
        credentials=credentials, client_options=client_options
    )
    try:
        import_documents(
            document_client,
            project,
            args.location,
            datastore_id,
            args.bucket,
            wait=args.wait,
        )
    except Exception as e:
        print(
            f"Import failed; rolling back by deleting {created.name!r}...",
            file=sys.stderr,
        )
        try:
            delete_datastore(datastore_client, created.name)
            print("Rollback succeeded.", file=sys.stderr)
        except Exception as cleanup_err:
            print(
                f"Rollback failed: {cleanup_err}\n"
                f"You may need to manually delete: {created.name}",
                file=sys.stderr,
            )
        raise DatastoreError(f"Import failed: {e}") from e
    console_url = (
        f"https://console.cloud.google.com/gen-app-builder/locations/{args.location}"
        f"/collections/default_collection/data-stores/{datastore_id}"
        f"/data/documents?project={project}"
    )
    print(
        f"\nDone. Your datastore ID is: {datastore_id}\n"
        f"View it in the GCP console: {console_url}\n"
        f"Next: run make create-app-gcs DATASTORE_ID={datastore_id} APP_ID=<id> to create and attach a Search app."
    )


if __name__ == "__main__":
    try:
        main()
    except DatastoreError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
