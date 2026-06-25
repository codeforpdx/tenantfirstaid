"""Tests for scripts.generate_metadata_jsonl."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.generate_metadata_jsonl import build_entries, infer_city


class TestInferCity:
    def test_state_level_file_returns_none(self):
        assert infer_city(Path("ORS090.txt")) is None

    def test_portland_returns_portland(self):
        assert infer_city(Path("portland/PCC30.01.txt")) == "portland"

    def test_eugene_returns_eugene(self):
        assert infer_city(Path("eugene/EHC8.txt")) == "eugene"

    def test_city_in_nested_subdir(self):
        assert infer_city(Path("portland/2025/PCC30.01.txt")) == "portland"

    def test_year_subdir_only_returns_none(self):
        assert infer_city(Path("2025/ORS090.txt")) is None


class TestBuildEntries:
    @pytest.fixture
    def doc_tree(self, tmp_path: Path) -> Path:
        (tmp_path / "2025").mkdir()
        (tmp_path / "portland").mkdir()
        (tmp_path / "eugene").mkdir()
        (tmp_path / "2025" / "ORS090.txt").write_text("state doc")
        (tmp_path / "portland" / "PCC30.01.txt").write_text("portland doc")
        (tmp_path / "eugene" / "EHC8.txt").write_text("eugene doc")
        return tmp_path

    def test_empty_scopes_returns_all(self, doc_tree: Path):
        assert len(build_entries(doc_tree, "my-bucket", set())) == 3

    def test_or_scope_returns_state_only(self, doc_tree: Path):
        entries = build_entries(doc_tree, "my-bucket", {"or"})
        assert len(entries) == 1
        assert entries[0].id == "ORS090"

    def test_portland_scope_returns_portland_only(self, doc_tree: Path):
        entries = build_entries(doc_tree, "my-bucket", {"portland"})
        assert len(entries) == 1
        assert entries[0].id == "PCC30.01"

    def test_multiple_scopes(self, doc_tree: Path):
        entries = build_entries(doc_tree, "my-bucket", {"portland", "eugene"})
        assert {e.id for e in entries} == {"PCC30.01", "EHC8"}

    def test_state_entry_structure(self, doc_tree: Path):
        entries = build_entries(doc_tree, "my-bucket", {"or"})
        entry = entries[0]
        assert entry.id == "ORS090"
        assert entry.struct_data == {"city": "null", "state": "or"}
        assert entry.content.mime_type == "text/plain"
        assert entry.content.uri == "gs://my-bucket/ORS090.txt"

    def test_city_entry_structure(self, doc_tree: Path):
        entries = build_entries(doc_tree, "my-bucket", {"portland"})
        entry = entries[0]
        assert entry.struct_data == {"city": "portland", "state": "or"}

    def test_uri_is_flat_not_mirrored(self, doc_tree: Path):
        """GCS files are uploaded flat; URIs must point to the bucket root."""
        entries = build_entries(doc_tree, "my-bucket", {"portland"})
        assert entries[0].content.uri == "gs://my-bucket/PCC30.01.txt"

    def test_duplicate_basename_raises(self, tmp_path: Path):
        (tmp_path / "2024").mkdir()
        (tmp_path / "2025").mkdir()
        (tmp_path / "2024" / "ORS090.txt").write_text("old")
        (tmp_path / "2025" / "ORS090.txt").write_text("new")
        with pytest.raises(RuntimeError, match="Duplicate document id"):
            build_entries(tmp_path, "my-bucket", set())

    def test_unknown_non_ascii_raises(self, tmp_path: Path):
        # Smoke test for the delegation; conversion cases live in test_enforce_ascii.py.
        (tmp_path / "ORS090.txt").write_text("café", encoding="utf-8")
        with pytest.raises(RuntimeError, match="failed ASCII validation"):
            build_entries(tmp_path, "my-bucket", set())


class TestMain:
    def test_missing_bucket_raises(self):
        with patch("sys.argv", ["generate_metadata_jsonl"]):
            from scripts.generate_metadata_jsonl import parse_args

            with pytest.raises(SystemExit):
                parse_args()

    def test_writes_valid_jsonl(self, tmp_path: Path):
        (tmp_path / "ORS090.txt").write_text("doc")
        output = tmp_path / "out.jsonl"

        with (
            patch("scripts.generate_metadata_jsonl.DOCUMENTS_DIR", tmp_path),
            patch("scripts.generate_metadata_jsonl.OUTPUT_FILE", output),
            patch("sys.argv", ["generate_metadata_jsonl", "--bucket", "test-bucket"]),
        ):
            from scripts.generate_metadata_jsonl import main

            main()

        lines = output.read_text().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["id"] == "ORS090"
        assert entry["content"]["uri"] == "gs://test-bucket/ORS090.txt"
