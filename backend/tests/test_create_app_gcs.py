"""Tests for scripts.create_app_gcs."""

from unittest.mock import MagicMock, patch

import pytest
from gcs_helpers import patch_singleton
from google.api_core import exceptions as gcp_exceptions

from scripts.create_app_gcs import (
    AppError,
    create_app,
    main,
    verify_datastore_exists,
)
from scripts.shared import collection_path


class TestCreateApp:
    def _make_client(
        self,
        engine_name: str = "projects/p/locations/global/collections/default_collection/engines/my-app",
    ):
        client = MagicMock()
        operation = MagicMock()
        result = MagicMock()
        result.name = engine_name
        operation.result.return_value = result
        client.create_engine.return_value = operation
        return client

    def test_creates_and_returns_engine(self):
        client = self._make_client()

        result = create_app(client, "my-project", "global", "my-app", "My App", "my-ds")

        client.create_engine.assert_called_once()
        request = client.create_engine.call_args.kwargs["request"]
        assert request.engine_id == "my-app"
        assert request.engine.display_name == "My App"
        assert request.engine.data_store_ids == ["my-ds"]
        assert request.parent == collection_path("my-project", "global")
        assert result is client.create_engine.return_value.result.return_value

    def test_already_exists_raises_app_error(self):
        client = MagicMock()
        client.create_engine.side_effect = gcp_exceptions.AlreadyExists("exists")

        with pytest.raises(AppError, match="already exists"):
            create_app(client, "my-project", "global", "my-app", "My App", "my-ds")


class TestVerifyDatastoreExists:
    def test_passes_when_datastore_exists(self):
        client = MagicMock()

        verify_datastore_exists(client, "my-project", "global", "my-ds")

        client.get_data_store.assert_called_once_with(
            name=f"{collection_path('my-project', 'global')}/dataStores/my-ds"
        )

    def test_not_found_raises_app_error(self):
        client = MagicMock()
        client.get_data_store.side_effect = gcp_exceptions.NotFound("missing")

        with pytest.raises(AppError, match="not found"):
            verify_datastore_exists(client, "my-project", "global", "my-ds")


class TestMain:
    _ARGV_BASE = ["create_app_gcs", "--datastore-id", "my-ds", "--app-id", "my-app"]

    def _patch_singleton(self):
        return patch_singleton("scripts.create_app_gcs.SINGLETON")

    def test_dry_run_does_not_call_api(self, capsys):
        with (
            self._patch_singleton(),
            patch(
                "scripts.create_app_gcs.discoveryengine.EngineServiceClient"
            ) as eng_cls,
            patch("sys.argv", [*self._ARGV_BASE, "--dry-run"]),
        ):
            main()

        eng_cls.assert_not_called()
        assert "[dry-run]" in capsys.readouterr().out

    def test_happy_path_creates_app(self, capsys):
        engine_client = MagicMock()
        created_engine = MagicMock()
        created_engine.name = (
            "projects/my-project/locations/global"
            "/collections/default_collection/engines/my-app"
        )
        operation = MagicMock()
        operation.result.return_value = created_engine
        engine_client.create_engine.return_value = operation

        with (
            self._patch_singleton(),
            patch("scripts.create_app_gcs.load_gcp_credentials"),
            patch("scripts.create_app_gcs.discoveryengine.DataStoreServiceClient"),
            patch(
                "scripts.create_app_gcs.discoveryengine.EngineServiceClient",
                return_value=engine_client,
            ),
            patch("sys.argv", self._ARGV_BASE),
        ):
            main()

        engine_client.create_engine.assert_called_once()
        out = capsys.readouterr().out
        assert "my-app" in out
        assert "VERTEX_AI_DATASTORE_LAWS=my-ds" in out

    def test_already_exists_raises_app_error(self):
        engine_client = MagicMock()
        engine_client.create_engine.side_effect = gcp_exceptions.AlreadyExists("exists")

        with (
            self._patch_singleton(),
            patch("scripts.create_app_gcs.load_gcp_credentials"),
            patch("scripts.create_app_gcs.discoveryengine.DataStoreServiceClient"),
            patch(
                "scripts.create_app_gcs.discoveryengine.EngineServiceClient",
                return_value=engine_client,
            ),
            patch("sys.argv", self._ARGV_BASE),
        ):
            with pytest.raises(AppError, match="already exists"):
                main()

    def test_missing_datastore_raises_before_creating_engine(self):
        datastore_client = MagicMock()
        datastore_client.get_data_store.side_effect = gcp_exceptions.NotFound("missing")
        engine_client = MagicMock()

        with (
            self._patch_singleton(),
            patch("scripts.create_app_gcs.load_gcp_credentials"),
            patch(
                "scripts.create_app_gcs.discoveryengine.DataStoreServiceClient",
                return_value=datastore_client,
            ),
            patch(
                "scripts.create_app_gcs.discoveryengine.EngineServiceClient",
                return_value=engine_client,
            ),
            patch("sys.argv", self._ARGV_BASE),
        ):
            with pytest.raises(AppError, match="not found"):
                main()

        engine_client.create_engine.assert_not_called()
