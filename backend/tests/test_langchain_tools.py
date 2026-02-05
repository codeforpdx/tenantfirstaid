"""
Test location sanitization and other methods
"""

from typing import Dict

from tenantfirstaid.langchain_tools import (
    CityStateLawsInputSchema,
    __filter_builder,
)
from tenantfirstaid.location import OregonCity, UsaState


def test_only_oregon_json_serialization():
    city = None
    beaver_state = UsaState("or")
    schema = CityStateLawsInputSchema(query="", city=city, state=beaver_state)
    d: Dict[str, str] = schema.model_dump(mode="json")
    assert d["city"] is None
    assert d["state"] == "or"


def test_eugene_oregon_json_serialization():
    city = OregonCity("eugene")
    beaver_state = UsaState("or")
    schema = CityStateLawsInputSchema(query="", city=city, state=beaver_state)
    d: Dict[str, str] = schema.model_dump(mode="json")
    assert d["city"] == "eugene"
    assert d["state"] == "or"


def test_portland_oregon_json_serialization():
    rose_city = OregonCity("portland")
    beaver_state = UsaState("or")
    schema = CityStateLawsInputSchema(query="", city=rose_city, state=beaver_state)
    d: Dict[str, str] = schema.model_dump(mode="json")
    assert d["city"] == "portland"
    assert d["state"] == "or"


# TODO: negative tests for input validation

# TODO: test _filter_builder


def test_retrieve_city_law_filters_correctly():
    """Test that city law retrieval uses correct filter."""
    state = UsaState.from_maybe_str("or")
    city = OregonCity.from_maybe_str("portland")

    filter = __filter_builder(state, city)

    # Verify filter was constructed correctly.
    assert 'city: ANY("portland")' in str(filter)
    assert 'state: ANY("or")' in str(filter)


def test_retrieve_state_law_filters_correctly():
    """Test that state law retrieval uses correct filter."""
    state = UsaState.from_maybe_str("or")
    city = None

    filter = __filter_builder(state, city)

    # Verify filter was constructed correctly.
    assert 'city: ANY("null")' in str(filter)
    assert 'state: ANY("or")' in str(filter)
