"""
ensure that only keys that should exist are readable
ensure that symbols are read-only
"""

from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    LETTER_TEMPLATE,
    OREGON_LAW_CENTER_PHONE_NUMBER,
    _GoogEnvAndPolicy,
    _parse_datastores,
    _strtobool,
)

# ── _strtobool property-based tests ───────────────────────────────────────────

_TRUTHY = ["y", "yes", "t", "true", "on", "1"]
_FALSY = ["n", "no", "f", "false", "off", "0"]
_RECOGNIZED = frozenset(_TRUTHY + _FALSY)


def _arbitrary_case(s: str) -> st.SearchStrategy[str]:
    """Strategy that generates arbitrary upper/lower casings of a fixed string."""
    return st.lists(st.booleans(), min_size=len(s), max_size=len(s)).map(
        lambda mask: "".join(c.upper() if up else c.lower() for c, up in zip(s, mask))
    )


@pytest.mark.property
@given(data=st.data(), word=st.sampled_from(_TRUTHY))
def test_strtobool_truthy_any_case(data, word):
    """All recognized truthy strings should return True in any casing."""
    assert _strtobool(data.draw(_arbitrary_case(word))) is True


@pytest.mark.property
@given(data=st.data(), word=st.sampled_from(_FALSY))
def test_strtobool_falsy_any_case(data, word):
    """All recognized falsy strings should return False in any casing."""
    assert _strtobool(data.draw(_arbitrary_case(word))) is False


@pytest.mark.property
@given(st.text().filter(lambda s: s.lower() not in _RECOGNIZED))
def test_strtobool_unrecognized_raises(s):
    """Any string outside the recognized set should raise ValueError."""
    with pytest.raises(ValueError):
        _strtobool(s)


def test_default_instructions_contains_oregon_law_center_phone():
    assert OREGON_LAW_CENTER_PHONE_NUMBER in DEFAULT_INSTRUCTIONS


def test_default_instructions_contains_citation_links():
    assert "oregon.public.law" in DEFAULT_INSTRUCTIONS


def test_letter_template_contains_placeholders():
    assert "[Your Name]" in LETTER_TEMPLATE
    assert "[Your Street Address]" in LETTER_TEMPLATE
    assert "ORS 90.320" in LETTER_TEMPLATE


class TestStrtobool:
    def test_none_returns_false(self):
        assert _strtobool(None) is False

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid truth value"):
            _strtobool("maybe")


class TestGoogEnvAndPolicy:
    REQUIRED_ENV = {
        "MODEL_NAME": "gemini-2.5-pro",
        "VERTEX_AI_DATASTORE_LAWS": "test-datastore",
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
        assert singleton.VERTEX_AI_DATASTORES["laws"] == "test-datastore"

    @pytest.mark.parametrize("missing_var", REQUIRED_ENV.keys())
    @patch("tenantfirstaid.constants.Path.exists", return_value=False)
    def test_missing_required_var_raises(self, mock_path, missing_var):
        env = {k: v for k, v in self.REQUIRED_ENV.items() if k != missing_var}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="environment variable is not set"):
                _GoogEnvAndPolicy()

    @patch("tenantfirstaid.constants.Path.exists", return_value=False)
    def test_missing_laws_datastore_raises(self, mock_path):
        env = {
            **self.REQUIRED_ENV,
            "VERTEX_AI_DATASTORE_OREGONLAWHELP": "store-1",
        }
        del env["VERTEX_AI_DATASTORE_LAWS"]
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="VERTEX_AI_DATASTORE_LAWS"):
                _GoogEnvAndPolicy()


class TestParseDatastores:
    def test_bare_id(self):
        result = _parse_datastores({"VERTEX_AI_DATASTORE_LAWS": "my-store"})
        assert result["laws"] == "my-store"

    def test_full_uri_extraction(self):
        result = _parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "projects/p/locations/l/dataStores/my-ds"}
        )
        assert result["laws"] == "my-ds"

    def test_full_uri_with_trailing_slash(self):
        result = _parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "projects/p/locations/l/dataStores/my-ds/"}
        )
        assert result["laws"] == "my-ds"

    def test_multiple_stores(self):
        result = _parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "store-1", "VERTEX_AI_DATASTORE_LETTERS": "store-2"}
        )
        assert result["laws"] == "store-1"
        assert result["letters"] == "store-2"

    def test_name_is_lowercased(self):
        result = _parse_datastores({"VERTEX_AI_DATASTORE_OREGON_LAW_HELP": "store-1"})
        assert result["oregon_law_help"] == "store-1"

    def test_whitespace_trimmed(self):
        result = _parse_datastores({"VERTEX_AI_DATASTORE_LAWS": "  my-store  "})
        assert result["laws"] == "my-store"

    def test_empty_value_raises(self):
        with pytest.raises(ValueError, match="set but empty"):
            _parse_datastores({"VERTEX_AI_DATASTORE_LAWS": ""})

    def test_non_prefixed_vars_ignored(self):
        result = _parse_datastores(
            {"VERTEX_AI_DATASTORE_LAWS": "store-1", "MODEL_NAME": "gemini-2.5-pro"}
        )
        assert set(result.keys()) == {"laws"}

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="has no name after the prefix"):
            _parse_datastores({"VERTEX_AI_DATASTORE_": "store-1"})

    def test_no_datastore_vars_returns_empty(self):
        result = _parse_datastores({"MODEL_NAME": "gemini-2.5-pro"})
        assert result == {}


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


def test_system_prompt_placeholders_are_substituted():
    """Ensure str.format() placeholders are resolved, not left raw."""
    assert "{RESPONSE_WORD_LIMIT}" not in DEFAULT_INSTRUCTIONS
    assert "{OREGON_LAW_CENTER_PHONE_NUMBER}" not in DEFAULT_INSTRUCTIONS


def test_system_prompt_has_no_stray_placeholders():
    """Guard against someone adding an unrecognised {placeholder} to system_prompt.md."""
    import re

    # Match {WORD} but not markdown links like [text](url) or tool names like `{text}`.
    stray = re.findall(r"(?<!\[)(?<!`)\{[A-Z_]+\}(?!`)(?!\])", DEFAULT_INSTRUCTIONS)
    assert stray == [], f"Unsubstituted placeholders found: {stray}"
