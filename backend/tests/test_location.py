import pytest

from tenantfirstaid.location import OregonCity, UsaState, city_or_state_input_sanitizer


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
