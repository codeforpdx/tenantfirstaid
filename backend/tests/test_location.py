import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenantfirstaid.location import OregonCity, UsaState, city_or_state_input_sanitizer


def _arbitrary_case(s: str) -> st.SearchStrategy[str]:
    """Strategy that generates arbitrary upper/lower casings of a fixed string."""
    return st.lists(st.booleans(), min_size=len(s), max_size=len(s)).map(
        lambda mask: "".join(c.upper() if up else c.lower() for c, up in zip(s, mask))
    )


def test_city_from_none():
    na = OregonCity.from_maybe_str(None)
    assert na is None


def test_city_from_empty():
    empty = OregonCity.from_maybe_str("")
    assert empty is None


def test_city_from_portland():
    pdx = OregonCity.from_maybe_str(" portland")
    assert pdx is OregonCity.PORTLAND


def test_city_from_eugene():
    eu = OregonCity.from_maybe_str("eugene ")
    assert eu is OregonCity.EUGENE


def test_state_from_none():
    na = UsaState.from_maybe_str(None)
    assert na is UsaState.OTHER


def test_state_from_empty():
    empty = UsaState.from_maybe_str("")
    assert empty is UsaState.OTHER


def test_state_from_or():
    beaver_state = UsaState.from_maybe_str(" oR")
    assert beaver_state is UsaState.OREGON


def test_state_from_other():
    other = UsaState.from_maybe_str(" sdf kj ")
    assert other is UsaState.OTHER


def test_city_lower():
    assert OregonCity.EUGENE.lower() == "eugene"


def test_sanitization():
    with pytest.raises(ValueError) as e:
        city_or_state_input_sanitizer("")
        assert "length" in str(e)

    with pytest.raises(ValueError) as e:
        city_or_state_input_sanitizer("a" * 10)
        assert "length" in str(e)

    with pytest.raises(ValueError) as e:
        city_or_state_input_sanitizer("a")
        assert "length" in str(e)

    with pytest.raises(ValueError) as e:
        city_or_state_input_sanitizer("123")
        assert "characters" in str(e)

    with pytest.raises(ValueError) as e:
        city_or_state_input_sanitizer("or ")
        assert "whitespace" in str(e)


# ── property-based tests ───────────────────────────────────────────────────────

_alpha_chars = st.characters(categories=["L"])


@given(st.text(alphabet=_alpha_chars, min_size=2, max_size=9))
def test_sanitizer_valid_input_returns_lowercase(s):
    """Any 2-9 letter string should be accepted and returned lowercased."""
    assert city_or_state_input_sanitizer(s) == s.lower()


@given(st.text(alphabet=_alpha_chars, min_size=10))
def test_sanitizer_too_long_raises(s):
    """Strings longer than 9 characters should be rejected."""
    with pytest.raises(ValueError, match="length"):
        city_or_state_input_sanitizer(s)


@given(st.text(alphabet=_alpha_chars, max_size=1))
def test_sanitizer_too_short_raises(s):
    """Strings shorter than 2 characters (including empty) should be rejected."""
    with pytest.raises(ValueError):
        city_or_state_input_sanitizer(s)


@given(st.text().filter(lambda s: not s.isalpha()))
def test_sanitizer_non_alpha_raises(s):
    """Strings with any non-alpha character should be rejected."""
    with pytest.raises(ValueError, match="characters"):
        city_or_state_input_sanitizer(s)


@given(st.just(None))
def test_sanitizer_none_returns_empty(s):
    assert city_or_state_input_sanitizer(s) == ""


@given(data=st.data(), city=st.sampled_from(list(OregonCity)))
def test_oregon_city_from_maybe_str_case_invariant(data, city):
    """OregonCity.from_maybe_str should accept any casing of a recognized city."""
    mixed = data.draw(_arbitrary_case(city.value))
    assert OregonCity.from_maybe_str(mixed) == city


@given(st.text().filter(lambda s: s.strip().lower() not in {"portland", "eugene"}))
def test_oregon_city_from_maybe_str_unrecognized_returns_none(s):
    """Any string that is not a recognized city name should return None."""
    assert OregonCity.from_maybe_str(s) is None


@given(data=st.data())
def test_usa_state_from_maybe_str_or_case_invariant(data):
    """UsaState.from_maybe_str should accept 'or' in any casing."""
    mixed = data.draw(_arbitrary_case("or"))
    assert UsaState.from_maybe_str(mixed) is UsaState.OREGON


@given(st.text().filter(lambda s: s.strip().upper() != "OR"))
def test_usa_state_from_maybe_str_non_oregon_returns_other(s):
    """Any string that is not 'or' (case-insensitive) should return OTHER."""
    assert UsaState.from_maybe_str(s) is UsaState.OTHER
