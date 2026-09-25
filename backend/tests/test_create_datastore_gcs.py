"""Tests for scripts.create_datastore_gcs."""

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from gcs_helpers import patch_gcp_env
from google.api_core import exceptions as gcp_exceptions
from google.cloud import discoveryengine_v1 as discoveryengine

from scripts.create_datastore_gcs import (
    GCS_DATA_SCHEMA,
    ROLLBACK_TIMEOUT_SECONDS,
    DatastoreError,
    _branch_path,
    check_bucket_location_compat,
    create_datastore,
    delete_datastore,
    import_documents,
    main,
)
from scripts.shared import collection_path

_DEFAULT_DS_NAME = (
    "projects/p/locations/global/collections/default_collection/dataStores/my-ds"
)


def _ds_client(name: str = _DEFAULT_DS_NAME) -> MagicMock:
    """DataStoreServiceClient mock whose create_data_store LRO returns a datastore with the given name."""
    client = MagicMock()
    created = MagicMock()
    created.name = name
    operation = MagicMock()
    operation.result.return_value = created
    client.create_data_store.return_value = operation
    return client


def _doc_client(
    *,
    success: int = 12,
    failure: int = 0,
    error_samples: list[MagicMock] | None = None,
) -> MagicMock:
    """DocumentServiceClient mock whose import_documents LRO reports the given counts."""
    client = MagicMock()
    operation = MagicMock()
    operation.operation.name = "operations/import-123"
    operation.result.return_value = MagicMock(error_samples=error_samples or [])
    operation.metadata = MagicMock(success_count=success, failure_count=failure)
    client.import_documents.return_value = operation
    return client


class TestCheckBucketLocationCompat:
    def _make_client(self, bucket_location: str) -> MagicMock:
        client = MagicMock()
        bucket = MagicMock()
        bucket.location = bucket_location
        client.get_bucket.return_value = bucket
        return client

    @pytest.mark.parametrize(
        "bucket_location,datastore_location",
        [
            ("US", "global"),
            ("EU", "global"),
            ("US-CENTRAL1", "global"),
            ("US", "us"),
            ("US-EAST1", "us"),
            ("EU", "eu"),
            ("EUROPE-WEST1", "eu"),
            ("EU-WEST1", "eu"),
        ],
    )
    def test_compatible_pairs_do_not_raise(self, bucket_location, datastore_location):
        client = self._make_client(bucket_location)
        check_bucket_location_compat(client, "my-bucket", datastore_location)

    @pytest.mark.parametrize(
        "bucket_location,datastore_location",
        [
            ("EU", "us"),
            ("EUROPE-WEST1", "us"),
            ("US", "eu"),
            ("US-CENTRAL1", "eu"),
        ],
    )
    def test_incompatible_pairs_raise_datastore_error(
        self, bucket_location, datastore_location
    ):
        client = self._make_client(bucket_location)
        with pytest.raises(DatastoreError, match="incompatible"):
            check_bucket_location_compat(client, "my-bucket", datastore_location)

    def test_error_message_includes_bucket_name_and_locations(self):
        client = self._make_client("EU")
        with pytest.raises(DatastoreError) as exc_info:
            check_bucket_location_compat(client, "my-bucket", "us")
        assert "my-bucket" in str(exc_info.value)
        assert "EU" in str(exc_info.value)
        assert "us" in str(exc_info.value)


class TestCreateDatastore:
    def test_creates_and_returns_datastore(self):
        client = _ds_client()

        result = create_datastore(client, "my-project", "global", "my-ds", "My DS")

        client.create_data_store.assert_called_once()
        request = client.create_data_store.call_args.kwargs["request"]
        assert request.data_store_id == "my-ds"
        assert request.data_store.display_name == "My DS"
        assert request.parent == collection_path("my-project", "global")
        assert result is client.create_data_store.return_value.result.return_value

    def test_already_exists_raises_datastore_error(self):
        client = MagicMock()
        client.create_data_store.side_effect = gcp_exceptions.AlreadyExists("exists")

        with pytest.raises(DatastoreError, match="already exists"):
            create_datastore(client, "my-project", "global", "my-ds", "My DS")


class TestImportDocuments:
    def test_wait_true_polls_and_prints_counts(self, capsys):
        client = _doc_client(success=10, failure=0)

        import_documents(
            client, "my-project", "global", "my-ds", "my-bucket", wait=True
        )

        client.import_documents.return_value.result.assert_called_once()
        out = capsys.readouterr().out
        assert "success=10" in out
        assert "failure=0" in out

    def test_wait_false_skips_polling(self, capsys):
        client = _doc_client()

        import_documents(
            client, "my-project", "global", "my-ds", "my-bucket", wait=False
        )

        client.import_documents.return_value.result.assert_not_called()
        assert "--no-wait" in capsys.readouterr().out

    def test_error_samples_are_printed(self, capsys):
        err = MagicMock()
        err.message = "bad doc"
        client = _doc_client(failure=1, error_samples=[err])

        import_documents(
            client, "my-project", "global", "my-ds", "my-bucket", wait=True
        )

        assert "bad doc" in capsys.readouterr().out

    def test_request_points_at_correct_bucket_and_branch(self):
        client = _doc_client()

        import_documents(
            client, "my-project", "global", "my-ds", "my-bucket", wait=False
        )

        request = client.import_documents.call_args.kwargs["request"]
        assert request.parent == _branch_path("my-project", "global", "my-ds")
        assert request.gcs_source.input_uris == ["gs://my-bucket/metadata.jsonl"]
        assert request.gcs_source.data_schema == GCS_DATA_SCHEMA
        assert (
            request.reconciliation_mode
            == discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL
        )


class TestDeleteDatastore:
    def test_calls_delete_and_waits(self):
        client = MagicMock()
        operation = MagicMock()
        client.delete_data_store.return_value = operation

        delete_datastore(client, "projects/p/locations/global/.../dataStores/my-ds")

        client.delete_data_store.assert_called_once()
        request = client.delete_data_store.call_args.kwargs["request"]
        assert request.name == "projects/p/locations/global/.../dataStores/my-ds"
        operation.result.assert_called_once_with(timeout=ROLLBACK_TIMEOUT_SECONDS)


class TestMain:
    _ARGV_BASE = [
        "create_datastore_gcs",
        "--bucket",
        "my-bucket",
        "--datastore-id",
        "my-ds",
    ]

    def _patch_gcp_env(self):
        return patch_gcp_env("scripts.create_datastore_gcs.gcp_env")

    def _patch_storage_client(self, bucket_location: str = "US"):
        storage_client = MagicMock()
        bucket = MagicMock()
        bucket.location = bucket_location
        storage_client.get_bucket.return_value = bucket
        return patch(
            "scripts.create_datastore_gcs.storage.Client",
            return_value=storage_client,
        )

    @contextlib.contextmanager
    def _patched_main(
        self,
        ds_client: MagicMock,
        doc_client: MagicMock,
        *,
        bucket_location: str = "US",
        argv: list[str] | None = None,
    ):
        """Patch the GCP environment, storage, both Discovery Engine clients, and argv around a main() call."""
        with (
            self._patch_gcp_env(),
            self._patch_storage_client(bucket_location=bucket_location),
            patch(
                "scripts.create_datastore_gcs.discoveryengine.DataStoreServiceClient",
                return_value=ds_client,
            ),
            patch(
                "scripts.create_datastore_gcs.discoveryengine.DocumentServiceClient",
                return_value=doc_client,
            ),
            patch("sys.argv", argv or self._ARGV_BASE),
        ):
            yield

    def test_dry_run_does_not_call_api(self, capsys):
        with (
            self._patch_gcp_env(),
            patch(
                "scripts.create_datastore_gcs.discoveryengine.DataStoreServiceClient"
            ) as ds_cls,
            patch(
                "scripts.create_datastore_gcs.discoveryengine.DocumentServiceClient"
            ) as doc_cls,
            patch("sys.argv", [*self._ARGV_BASE, "--dry-run"]),
        ):
            main()

        ds_cls.assert_not_called()
        doc_cls.assert_not_called()
        assert "[dry-run]" in capsys.readouterr().out

    def test_happy_path_creates_datastore_and_imports(self):
        ds_client = _ds_client()
        doc_client = _doc_client()

        with self._patched_main(ds_client, doc_client):
            main()

        ds_client.create_data_store.assert_called_once()
        doc_client.import_documents.assert_called_once()

    def test_incompatible_bucket_location_raises_before_api_calls(self):
        ds_client = MagicMock()

        with self._patched_main(
            ds_client,
            MagicMock(),
            bucket_location="EU",
            argv=[*self._ARGV_BASE, "--location", "us"],
        ):
            with pytest.raises(DatastoreError, match="incompatible"):
                main()

        ds_client.create_data_store.assert_not_called()

    def test_already_exists_raises_datastore_error(self):
        ds_client = MagicMock()
        ds_client.create_data_store.side_effect = gcp_exceptions.AlreadyExists("exists")

        with self._patched_main(ds_client, MagicMock()):
            with pytest.raises(DatastoreError, match="already exists"):
                main()

    def test_import_failure_rolls_back_datastore(self):
        ds_client = _ds_client()
        doc_client = MagicMock()
        doc_client.import_documents.side_effect = RuntimeError("network timeout")

        with self._patched_main(ds_client, doc_client):
            with pytest.raises(DatastoreError, match="Import failed"):
                main()

        ds_client.delete_data_store.assert_called_once()

    def test_import_failure_with_cleanup_error_reports_manual_step(self, capsys):
        ds_client = _ds_client()
        ds_client.delete_data_store.side_effect = RuntimeError("permission denied")
        doc_client = MagicMock()
        doc_client.import_documents.side_effect = RuntimeError("network timeout")

        with self._patched_main(ds_client, doc_client):
            with pytest.raises(DatastoreError, match="Import failed"):
                main()

        err = capsys.readouterr().err
        assert "Rollback failed" in err
        assert _DEFAULT_DS_NAME in err
