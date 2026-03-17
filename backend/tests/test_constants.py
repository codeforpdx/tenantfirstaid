"""
ensure that only keys that should exist are readable
ensure that symbols are read-only
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenantfirstaid.constants import (
    DEFAULT_INSTRUCTIONS,
    LETTER_TEMPLATE,
    OREGON_LAW_CENTER_PHONE_NUMBER,
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
