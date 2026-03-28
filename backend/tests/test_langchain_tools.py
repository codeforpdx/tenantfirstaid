"""
Test location sanitization and other methods
"""

import inspect
from typing import Dict
from unittest.mock import MagicMock, patch

from tenantfirstaid.langchain_tools import (
    CityStateLawsInputSchema,
    __filter_builder,
    generate_letter,
    get_letter_template,
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


@patch("tenantfirstaid.langchain_tools.get_stream_writer")
def test_generate_letter_writes_letter_chunk(mock_get_stream_writer):
    """Test that generate_letter emits a letter chunk via the stream writer."""
    mock_writer = MagicMock()
    mock_get_stream_writer.return_value = mock_writer

    letter_content = "Dear Landlord,\n\nPlease fix the heater.\n\nSincerely,\nTenant"
    result = generate_letter.func(letter=letter_content)  # type: ignore[union-attr]

    mock_writer.assert_called_once_with({"type": "letter", "content": letter_content})
    assert result == "Letter generated successfully."


def test_get_letter_template_returns_template():
    """Test that get_letter_template returns the letter template content."""
    result = get_letter_template.invoke("")
    assert "[Your Name]" in result
    assert "ORS 90.320" in result


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
    func_params = set(
        inspect.signature(retrieve_city_state_laws.func).parameters.keys()  # type: ignore[unresolved-attribute]
    )
    func_params.discard("runtime")

    assert schema_fields == func_params


@patch("tenantfirstaid.langchain_tools.Rag_Builder")
def test_retrieve_city_state_laws_returns_joined_docs(mock_rag_class):
    """Test that RAG results are joined with newlines."""
    mock_rag_class.return_value.search.return_value = "Doc1 content\nDoc2 content"

    result = retrieve_city_state_laws.func(
        query="eviction notice",
        state=UsaState("or"),
        city=OregonCity("portland"),
        runtime=MagicMock(),
    )
    assert "Doc1 content" in result
    assert "Doc2 content" in result


@patch("tenantfirstaid.langchain_tools.Rag_Builder")
def test_retrieve_city_state_laws_empty_results(mock_rag_class):
    """Test behavior when RAG returns no documents."""
    mock_rag_class.return_value.search.return_value = ""

    result = retrieve_city_state_laws.func(
        query="obscure law",
        state=UsaState("or"),
        runtime=MagicMock(),
    )
    assert result == ""


def test_filter_builder_state_only():
    """Test filter with state only (no city) produces null city."""
    result = __filter_builder(UsaState("or"), None)
    assert 'city: ANY("null")' in result
    assert 'state: ANY("or")' in result


def test_filter_builder_with_city():
    """Test filter with city and state."""
    result = __filter_builder(UsaState("or"), OregonCity("eugene"))
    assert 'city: ANY("eugene")' in result
    assert 'state: ANY("or")' in result


@patch("tenantfirstaid.langchain_tools.get_stream_writer")
def test_generate_letter_empty_string(mock_get_stream_writer):
    """Test generate_letter with empty string."""
    mock_writer = MagicMock()
    mock_get_stream_writer.return_value = mock_writer

    result = generate_letter.func(letter="")
    mock_writer.assert_called_once_with({"type": "letter", "content": ""})
    assert result == "Letter generated successfully."
