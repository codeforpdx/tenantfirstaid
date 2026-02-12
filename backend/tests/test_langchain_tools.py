"""
Test location sanitization and other methods
"""

import inspect
from typing import Dict
from unittest.mock import MagicMock, patch

from tenantfirstaid.langchain_tools import (
    CityStateLawsInputSchema,
    __filter_builder,
    retrieve_city_state_laws,
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


@patch("tenantfirstaid.langchain_tools.Rag_Builder")
def test_retrieve_city_state_laws_state_only(mock_rag_class):
    """Test tool can be invoked with only state parameter."""
    mock_rag_class.return_value.search.return_value = ""

    # Should not raise despite city being omitted.
    retrieve_city_state_laws.func(  # type: ignore[union-attr]
        query="late rent fee", state=UsaState("or"), runtime=MagicMock()
    )


@patch("tenantfirstaid.langchain_tools.Rag_Builder")
def test_retrieve_city_state_laws_parameter_order(mock_rag_class):
    """Test that parameters are correctly ordered."""
    mock_rag_class.return_value.search.return_value = ""

    # Pass city before state (opposite of function signature order).
    retrieve_city_state_laws.func(  # type: ignore[union-attr]
        query="eviction notice",
        city=OregonCity("portland"),
        state=UsaState("or"),
        runtime=MagicMock(),
    )

    filter_arg = mock_rag_class.call_args[1]["filter"]
    assert "portland" in filter_arg and "or" in filter_arg


def test_tool_schema_matches_function_signature():
    """Test that Pydantic schema matches function defaults."""
    schema_fields = set(CityStateLawsInputSchema.model_fields.keys())
    func_params = set(inspect.signature(retrieve_city_state_laws.func).parameters.keys())  # type: ignore[union-attr]
    func_params.discard("runtime")

    assert schema_fields == func_params
