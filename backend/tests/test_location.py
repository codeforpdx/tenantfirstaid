import pytest

from tenantfirstaid.location import (
    Location,
    OregonCity,
    TFAAgentStateSchema,
    UsaState,
    city_or_state_input_sanitizer,
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


class TestLocationModel:
    def test_construct_with_city_and_state(self):
        loc = Location(city=OregonCity.PORTLAND, state=UsaState.OREGON)
        assert loc.city == OregonCity.PORTLAND
        assert loc.state == UsaState.OREGON

    def test_construct_defaults_to_none(self):
        loc = Location()
        assert loc.city is None
        assert loc.state is None

    def test_json_serialization(self):
        loc = Location(city=OregonCity.EUGENE, state=UsaState.OREGON)
        d = loc.model_dump(mode="json")
        assert d["city"] == "eugene"
        assert d["state"] == "or"


class TestTFAAgentStateSchema:
    def test_has_expected_fields(self):
        fields = TFAAgentStateSchema.__annotations__
        assert "state" in fields
        assert "city" in fields
        assert "messages" in fields


class TestSanitizerBoundary:
    def test_exactly_two_chars(self):
        assert city_or_state_input_sanitizer("or") == "or"

    def test_exactly_max_chars(self):
        assert city_or_state_input_sanitizer("abcdefghi") == "abcdefghi"

    def test_one_char_raises(self):
        with pytest.raises(ValueError, match="length"):
            city_or_state_input_sanitizer("a")

    def test_ten_chars_raises(self):
        with pytest.raises(ValueError, match="length"):
            city_or_state_input_sanitizer("abcdefghij")

    def test_none_returns_empty_string(self):
        assert city_or_state_input_sanitizer(None) == ""
