"""
ensure that only keys that should exist are readable
ensure that symbols are read-only
"""

from unittest.mock import patch

import pytest

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    LETTER_TEMPLATE,
    OREGON_LAW_CENTER_PHONE_NUMBER,
    _GoogEnvAndPolicy,
    _strtobool,
)


def test_default_instructions_contains_oregon_law_center_phone():
    assert OREGON_LAW_CENTER_PHONE_NUMBER in DEFAULT_INSTRUCTIONS


def test_default_instructions_contains_citation_links():
    assert "oregon.public.law" in DEFAULT_INSTRUCTIONS


def test_letter_template_contains_placeholders():
    assert "[Your Name]" in LETTER_TEMPLATE
    assert "[Your Street Address]" in LETTER_TEMPLATE
    assert "ORS 90.320" in LETTER_TEMPLATE


def test_import_constants():
    from tenantfirstaid.constants import SINGLETON

    assert SINGLETON is not None


class TestStrtobool:
    @pytest.mark.parametrize(
        "val,expected",
        [
            ("y", True),
            ("yes", True),
            ("t", True),
            ("true", True),
            ("on", True),
            ("1", True),
            ("YES", True),
            ("True", True),
            ("n", False),
            ("no", False),
            ("f", False),
            ("false", False),
            ("off", False),
            ("0", False),
            ("NO", False),
            ("False", False),
        ],
    )
    def test_valid_values(self, val, expected):
        assert _strtobool(val) is expected

    def test_none_returns_false(self):
        assert _strtobool(None) is False

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid truth value"):
            _strtobool("maybe")


class TestGoogEnvAndPolicy:
    REQUIRED_ENV = {
        "MODEL_NAME": "gemini-2.5-pro",
        "VERTEX_AI_DATASTORE": "test-datastore",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/creds.json",
    }

    @patch("tenantfirstaid.constants.Path.exists", return_value=False)
    @patch.dict("os.environ", REQUIRED_ENV, clear=False)
    def test_init_with_all_vars(self, mock_path):
        singleton = _GoogEnvAndPolicy()
        assert singleton.MODEL_NAME == "gemini-2.5-pro"
        assert singleton.GOOGLE_CLOUD_PROJECT == "test-project"

    @patch("tenantfirstaid.constants.Path.exists", return_value=False)
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_required_var_raises(self, mock_path):
        with pytest.raises(ValueError, match="environment variable is not set"):
            _GoogEnvAndPolicy()

    @patch("tenantfirstaid.constants.Path.exists", return_value=False)
    @patch.dict(
        "os.environ",
        {
            **REQUIRED_ENV,
            "VERTEX_AI_DATASTORE": "projects/p/locations/l/dataStores/my-ds",
        },
        clear=False,
    )
    def test_vertex_ai_datastore_uri_extraction(self, mock_path):
        singleton = _GoogEnvAndPolicy()
        assert singleton.VERTEX_AI_DATASTORE == "my-ds"


def test_model_config_values():
    """Pin model config values that affect legal advice quality.

    Low temperature and top_p produce consistent, citation-heavy responses
    rather than creative ones. Changing these accidentally could degrade the
    quality of legal guidance, so this test should break loudly.
    """
    from tenantfirstaid.constants import SINGLETON

    assert SINGLETON.MODEL_TEMPERATURE == 0.1
    assert SINGLETON.TOP_P == 0.1
    assert SINGLETON.MAX_TOKENS == 65535
    assert isinstance(SINGLETON.SAFETY_SETTINGS, dict)
    assert len(SINGLETON.SAFETY_SETTINGS) == 5
