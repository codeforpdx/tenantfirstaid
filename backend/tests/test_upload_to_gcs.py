"""Tests for scripts.upload_to_gcs."""

import contextlib
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from gcs_helpers import patch_singleton
from google.api_core import exceptions as gcp_exceptions

from scripts.upload_to_gcs import (
    UploadError,
    create_bucket,
    plan_upload,
    upload_files,
)


@contextlib.contextmanager
def _silence_stdout():
    """Suppress stdout so script print() output doesn't clutter the test report."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def _write_metadata(path: Path, bucket: str, names: list[str]) -> None:
    """Write a minimal metadata.jsonl with one entry per name."""
    with path.open("w") as f:
        for name in names:
            entry = {
                "id": Path(name).stem,
                "structData": {"city": None, "state": "or"},
                "content": {
                    "mimeType": "text/plain",
                    "uri": f"gs://{bucket}/{name}",
                },
            }
            f.write(json.dumps(entry) + "\n")


class TestPlanUpload:
    def test_resolves_files(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ORS090.txt").write_text("doc1")
        (docs / "subdir").mkdir()
        (docs / "subdir" / "ORS091.txt").write_text("doc2")

        metadata = tmp_path / "metadata.jsonl"
        _write_metadata(metadata, "my-bucket", ["ORS090.txt", "ORS091.txt"])

        name_to_path, returned_metadata = plan_upload("my-bucket", metadata, docs)

        assert returned_metadata == metadata
        assert set(name_to_path.keys()) == {"ORS090.txt", "ORS091.txt"}
        assert name_to_path["ORS090.txt"] == docs / "ORS090.txt"
        assert name_to_path["ORS091.txt"] == docs / "subdir" / "ORS091.txt"

    def test_missing_metadata_file_raises(self, tmp_path: Path):
        with pytest.raises(UploadError, match="metadata.jsonl not found"):
            plan_upload("my-bucket", tmp_path / "missing.jsonl", tmp_path)

    def test_wrong_bucket_in_uri_raises(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ORS090.txt").write_text("doc1")
        metadata = tmp_path / "metadata.jsonl"
        _write_metadata(metadata, "other-bucket", ["ORS090.txt"])

        with pytest.raises(UploadError, match="points at bucket 'other-bucket'"):
            plan_upload("my-bucket", metadata, docs)

    def test_missing_file_raises(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        metadata = tmp_path / "metadata.jsonl"
        _write_metadata(metadata, "my-bucket", ["MISSING.txt"])

        with pytest.raises(UploadError, match="MISSING.txt"):
            plan_upload("my-bucket", metadata, docs)

    def test_invalid_uri_scheme_raises(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        metadata = tmp_path / "metadata.jsonl"
        metadata.write_text(
            json.dumps(
                {
                    "id": "ORS090",
                    "content": {"mimeType": "text/plain", "uri": "http://x/y.txt"},
                }
            )
            + "\n"
        )
        with pytest.raises(UploadError, match="not a gs:// URI"):
            plan_upload("my-bucket", metadata, docs)

    def test_uri_with_subpath_rejected(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        metadata = tmp_path / "metadata.jsonl"
        metadata.write_text(
            json.dumps(
                {
                    "id": "ORS090",
                    "content": {
                        "mimeType": "text/plain",
                        "uri": "gs://my-bucket/2024/ORS090.txt",
                    },
                }
            )
            + "\n"
        )
        with pytest.raises(UploadError, match="subpath"):
            plan_upload("my-bucket", metadata, docs)

    def test_invalid_json_raises(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        metadata = tmp_path / "metadata.jsonl"
        metadata.write_text("not json\n")
        with pytest.raises(UploadError, match=r"metadata\.jsonl:1:"):
            plan_upload("my-bucket", metadata, docs)

    def test_unknown_field_raises(self, tmp_path: Path):
        # Unknown fields fail loud rather than silently parsing.
        docs = tmp_path / "docs"
        docs.mkdir()
        metadata = tmp_path / "metadata.jsonl"
        metadata.write_text('{"id": "X", "unknown_field": 1}\n')
        with pytest.raises(UploadError, match=r"metadata\.jsonl:1:"):
            plan_upload("my-bucket", metadata, docs)

    def test_blank_lines_skipped(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ORS090.txt").write_text("doc")
        metadata = tmp_path / "metadata.jsonl"
        metadata.write_text(
            json.dumps(
                {
                    "id": "ORS090",
                    "content": {
                        "mimeType": "text/plain",
                        "uri": "gs://my-bucket/ORS090.txt",
                    },
                }
            )
            + "\n\n"
        )
        name_to_path, _ = plan_upload("my-bucket", metadata, docs)
        assert set(name_to_path.keys()) == {"ORS090.txt"}


class TestCreateBucket:
    def test_creates_when_absent(self):
        client = MagicMock()
        bucket = MagicMock()
        client.create_bucket.return_value = bucket

        result = create_bucket(client, "new-bucket", "US")

        assert result is bucket
        client.create_bucket.assert_called_once_with("new-bucket", location="US")

    def test_fails_when_exists(self):
        client = MagicMock()
        client.create_bucket.side_effect = gcp_exceptions.Conflict("already exists")

        with pytest.raises(UploadError, match="already exists"):
            create_bucket(client, "taken", "US")


class TestUploadFiles:
    def test_uploads_each_file_and_metadata(self, tmp_path: Path):
        bucket_obj = MagicMock()
        # Distinct mock per blob() so we can assert each upload separately.
        blobs: dict[str, MagicMock] = {}

        def blob_factory(name):
            blob = MagicMock()
            blobs[name] = blob
            return blob

        bucket_obj.blob.side_effect = blob_factory

        a = tmp_path / "a.txt"
        a.write_text("a")
        b = tmp_path / "b.txt"
        b.write_text("b")
        metadata = tmp_path / "metadata.jsonl"
        metadata.write_text("{}")

        with _silence_stdout():
            upload_files(bucket_obj, {"a.txt": a, "b.txt": b}, metadata)

        assert set(blobs.keys()) == {"a.txt", "b.txt", "metadata.jsonl"}
        blobs["a.txt"].upload_from_filename.assert_called_once_with(
            str(a), content_type="text/plain"
        )
        blobs["b.txt"].upload_from_filename.assert_called_once_with(
            str(b), content_type="text/plain"
        )
        blobs["metadata.jsonl"].upload_from_filename.assert_called_once_with(
            str(metadata), content_type="application/jsonl"
        )


class TestMain:
    def test_dry_run_does_not_call_storage(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ORS090.txt").write_text("doc")
        metadata = tmp_path / "metadata.jsonl"
        _write_metadata(metadata, "my-bucket", ["ORS090.txt"])

        with (
            patch("scripts.upload_to_gcs.storage.Client") as client_cls,
            patch(
                "sys.argv",
                [
                    "upload_to_gcs",
                    "--bucket",
                    "my-bucket",
                    "--metadata",
                    str(metadata),
                    "--documents-dir",
                    str(docs),
                    "--dry-run",
                ],
            ),
        ):
            from scripts.upload_to_gcs import main

            with _silence_stdout():
                main()

        client_cls.assert_not_called()

    def test_happy_path_creates_bucket_and_uploads(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ORS090.txt").write_text("doc")
        metadata = tmp_path / "metadata.jsonl"
        _write_metadata(metadata, "fresh-bucket", ["ORS090.txt"])

        bucket_obj = MagicMock()
        blob = MagicMock()
        bucket_obj.blob.return_value = blob

        with (
            patch_singleton("scripts.upload_to_gcs.SINGLETON"),
            patch("scripts.upload_to_gcs.storage.Client") as client_cls,
            patch("scripts.upload_to_gcs.load_gcp_credentials"),
            patch(
                "sys.argv",
                [
                    "upload_to_gcs",
                    "--bucket",
                    "fresh-bucket",
                    "--metadata",
                    str(metadata),
                    "--documents-dir",
                    str(docs),
                ],
            ),
        ):
            client_cls.return_value.create_bucket.return_value = bucket_obj

            from scripts.upload_to_gcs import main

            with _silence_stdout():
                main()

        # The bucket is created in the configured project, not the credentials' default.
        assert client_cls.call_args.kwargs["project"] == "my-project"
        client_cls.return_value.create_bucket.assert_called_once_with(
            "fresh-bucket", location="US"
        )
        # Two uploads: the doc and metadata.jsonl.
        assert blob.upload_from_filename.call_count == 2
