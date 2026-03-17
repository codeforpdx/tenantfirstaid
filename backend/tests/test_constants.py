"""
ensure that only keys that should exist are readable
ensure that symbols are read-only
"""

from unittest.mock import patch

import pytest

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    LETTER_TEMPLATE,
    OREGON_LAW_CENTER_PHONE_NUMBER,
    _GoogEnvAndPolicy,
    _strtobool,
    _strtobool,
)


# ── _strtobool property-based tests ───────────────────────────────────────────

_TRUTHY = ["y", "yes", "t", "true", "on", "1"]
_FALSY = ["n", "no", "f", "false", "off", "0"]
_RECOGNIZED = frozenset(_TRUTHY + _FALSY)


def _arbitrary_case(s: str) -> st.SearchStrategy[str]:
    """Strategy that generates arbitrary upper/lower casings of a fixed string."""
    return st.lists(
        st.booleans(), min_size=len(s), max_size=len(s)
    ).map(lambda mask: "".join(c.upper() if up else c.lower() for c, up in zip(s, mask)))


@given(data=st.data(), word=st.sampled_from(_TRUTHY))
def test_strtobool_truthy_any_case(data, word):
    """All recognized truthy strings should return True in any casing."""
    assert _strtobool(data.draw(_arbitrary_case(word))) is True


@given(data=st.data(), word=st.sampled_from(_FALSY))
def test_strtobool_falsy_any_case(data, word):
    """All recognized falsy strings should return False in any casing."""
    assert _strtobool(data.draw(_arbitrary_case(word))) is False


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
