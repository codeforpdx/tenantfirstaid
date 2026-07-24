"""Create a Vertex AI Search app and link it to an existing datastore.

Companion to scripts.create_datastore_gcs. Run via `make create-app-gcs`.
"""

import argparse
import sys
from typing import cast

from google.api_core import exceptions as gcp_exceptions
from google.cloud import discoveryengine_v1 as discoveryengine

from scripts.shared import collection_path, datastore_path, validate_resource_name
from tenantfirstaid.constants import DEFAULT_VERTEX_AI_SEARCH_LOCATION, SINGLETON
from tenantfirstaid.google_auth import (
    discoveryengine_client_options,
    load_gcp_credentials,
)


class AppError(RuntimeError):
    """Raised when the app creation pipeline cannot proceed."""


def _engine_path(project: str, location: str, engine_id: str) -> str:
    return f"{collection_path(project, location)}/engines/{engine_id}"


def verify_datastore_exists(
    client: discoveryengine.DataStoreServiceClient,
    project: str,
    location: str,
    datastore_id: str,
) -> None:
    """Fail fast if datastore_id does not exist, before creating the app."""
    name = datastore_path(project, location, datastore_id)
    try:
        client.get_data_store(name=name)
    except gcp_exceptions.NotFound as e:
        raise AppError(
            f"Datastore {datastore_id!r} not found under {collection_path(project, location)}. "
            "Check --datastore-id, or run create-datastore-gcs first."
        ) from e


def create_app(
    client: discoveryengine.EngineServiceClient,
    project: str,
    location: str,
    engine_id: str,
    display_name: str,
    datastore_id: str,
) -> discoveryengine.Engine:
    """Create a Search app linked to datastore_id. Fails if engine_id already exists."""
    parent = collection_path(project, location)
    engine = discoveryengine.Engine(
        display_name=display_name,
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=[datastore_id],
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            # Standard is sufficient for keyword + semantic search; upgrade to Enterprise
            # if advanced LLM features are needed.
            search_tier=discoveryengine.SearchTier.SEARCH_TIER_STANDARD,
        ),
    )
    request = discoveryengine.CreateEngineRequest(
        parent=parent,
        engine=engine,
        engine_id=engine_id,
    )
    try:
        operation = client.create_engine(request=request)
    except gcp_exceptions.AlreadyExists as e:
        raise AppError(
            f"App {engine_id!r} already exists under {parent}. "
            "Pick a different APP_ID or delete the existing app first. BUT DO NOT DELETE/REPLACE A PRODUCTION APP!!!"
        ) from e

    return cast(discoveryengine.Engine, operation.result())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--datastore-id",
        required=True,
        type=validate_resource_name,
        help="Datastore ID to attach to the app (the ID printed by create-datastore-gcs).",
    )
    parser.add_argument(
        "--app-id",
        required=True,
        type=validate_resource_name,
        help="Resource ID for the new Search app. Lowercase letters, digits, hyphens; must begin with a letter or digit (1-63 chars). You choose this.",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="Human-readable display name (default: app ID).",
    )
    parser.add_argument(
        "--location",
        default=DEFAULT_VERTEX_AI_SEARCH_LOCATION,
        help=(
            f"Vertex AI Search location (default: {DEFAULT_VERTEX_AI_SEARCH_LOCATION}). "
            "Must match the location used in create-datastore-gcs."
        ),
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
    display_name = args.display_name or args.app_id

    print(
        f"Plan: create Search app {_engine_path(project, args.location, args.app_id)!r} "
        f"(display_name={display_name!r}) linked to datastore {args.datastore_id!r}."
    )

    if args.dry_run:
        print("[dry-run] no Discovery Engine API calls made.")
        return

    credentials = load_gcp_credentials(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)
    client_options = discoveryengine_client_options(args.location)

    datastore_client = discoveryengine.DataStoreServiceClient(
        credentials=credentials, client_options=client_options
    )
    verify_datastore_exists(datastore_client, project, args.location, args.datastore_id)

    engine_client = discoveryengine.EngineServiceClient(
        credentials=credentials, client_options=client_options
    )
    create_app(
        engine_client,
        project,
        args.location,
        args.app_id,
        display_name,
        args.datastore_id,
    )
    console_url = (
        f"https://console.cloud.google.com/gen-app-builder/locations/{args.location}"
        f"/collections/default_collection/engines/{args.app_id}"
        f"?project={project}"
    )
    print(
        f"\nDone. Your app ID is: {args.app_id}\n"
        f"View it in the GCP console: {console_url}\n"
        f"Set VERTEX_AI_DATASTORE_LAWS={args.datastore_id} in your .env."
    )


if __name__ == "__main__":
    try:
        main()
    except AppError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
