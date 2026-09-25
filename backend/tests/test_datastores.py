"""Tests for the env-free datastore module: parsing and the corpus configuration."""

import pytest

from tenantfirstaid.datastores import parse_datastores


class TestParseDatastores:
    def test_bare_id(self):
        result = parse_datastores({"VERTEX_AI_DATASTORE_LAWS": "my-store"})
        assert result["laws"] == "my-store"

    def test_full_uri_extraction(self):
        result = parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "projects/p/locations/l/dataStores/my-ds"}
        )
        assert result["laws"] == "my-ds"

    def test_full_uri_with_trailing_slash(self):
        result = parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "projects/p/locations/l/dataStores/my-ds/"}
        )
        assert result["laws"] == "my-ds"

    def test_multiple_stores(self):
        result = parse_datastores(
            {
                "VERTEX_AI_DATASTORE_LAWS": "store-1",
                "VERTEX_AI_DATASTORE_LETTERS": "store-2",
            }
        )
        assert result["laws"] == "store-1"
        assert result["letters"] == "store-2"

    def test_name_is_lowercased(self):
        result = parse_datastores({"VERTEX_AI_DATASTORE_OREGON_LAW_HELP": "store-1"})
        assert result["oregon_law_help"] == "store-1"

    def test_whitespace_trimmed(self):
        result = parse_datastores({"VERTEX_AI_DATASTORE_LAWS": "  my-store  "})
        assert result["laws"] == "my-store"

    def test_empty_value_raises(self):
        with pytest.raises(ValueError, match="set but empty"):
            parse_datastores({"VERTEX_AI_DATASTORE_LAWS": ""})

    def test_non_prefixed_vars_ignored(self):
        result = parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "store-1", "MODEL_NAME": "gemini-2.5-pro"}
        )
        assert set(result.keys()) == {"laws"}

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="has no name after the prefix"):
            parse_datastores({"VERTEX_AI_DATASTORE_": "store-1"})

    def test_no_datastore_vars_returns_empty(self):
        result = parse_datastores({"MODEL_NAME": "gemini-2.5-pro"})
        assert result == {}
