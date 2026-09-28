"""Tests for the model half of the configuration."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tenantfirstaid.google_models import _strtobool

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
@settings(
    deadline=None
)  # _strtobool is trivial; deadline only catches cold-start noise.
@given(data=st.data(), word=st.sampled_from(_TRUTHY))
def test_strtobool_truthy_any_case(data, word):
    """All recognized truthy strings should return True in any casing."""
    assert _strtobool(data.draw(_arbitrary_case(word))) is True


@pytest.mark.property
@settings(
    deadline=None
)  # _strtobool is trivial; deadline only catches cold-start noise.
@given(data=st.data(), word=st.sampled_from(_FALSY))
def test_strtobool_falsy_any_case(data, word):
    """All recognized falsy strings should return False in any casing."""
    assert _strtobool(data.draw(_arbitrary_case(word))) is False


@pytest.mark.property
@settings(
    deadline=None
)  # _strtobool is trivial; deadline only catches cold-start noise.
@given(st.text().filter(lambda s: s.strip().lower() not in _RECOGNIZED))
def test_strtobool_unrecognized_raises(s):
    """Any string outside the recognized set should raise ValueError.

    Filters on the stripped, lowercased form -- _strtobool strips before
    matching, so e.g. " true " is recognized and must not land here.
    """
    with pytest.raises(ValueError):
        _strtobool(s)


class TestStrtobool:
    def test_none_returns_false(self):
        assert _strtobool(None) is False

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid truth value"):
            _strtobool("maybe")

    def test_surrounding_whitespace_is_stripped(self):
        """SHOW_MODEL_THINKING=" true" should not raise, matching the treatment
        GcpEnvironment.from_env and ModelConfig.from_env give their variables.
        """
        assert _strtobool(" true\n") is True
        assert _strtobool("  false  ") is False
