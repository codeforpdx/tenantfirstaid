"""
Test location sanitization and other methods
"""

import inspect
from typing import Dict
from unittest.mock import MagicMock, patch

import grpc
from langchain_core.documents import Document

from tenantfirstaid.langchain_tools import (
    CityStateLawsInputSchema,
    Rag_Builder,
    __filter_builder,
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
    assert d["max_documents"] == 3
    assert d["get_extractive_answers"] is True


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


def test_schema_max_documents_bounds():
    """Schema should reject max_documents outside [1, 10]."""
    import pytest
    from pydantic import ValidationError

    state = UsaState("or")
    with pytest.raises(ValidationError):
        CityStateLawsInputSchema(query="", state=state, max_documents=0)
    with pytest.raises(ValidationError):
        CityStateLawsInputSchema(query="", state=state, max_documents=11)


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


@patch("tenantfirstaid.langchain_tools.Rag_Builder")
def test_retrieve_city_state_laws_custom_retrieval_params(mock_rag_class):
    """Test that max_documents and get_extractive_answers are forwarded to Rag_Builder."""
    mock_rag_class.return_value.search.return_value = "some result"

    retrieve_city_state_laws.func(  # type: ignore[union-attr]
        query="abandoned property",
        state=UsaState("or"),
        max_documents=5,
        get_extractive_answers=False,
        runtime=MagicMock(),
    )

    call_kwargs = mock_rag_class.call_args[1]
    assert call_kwargs["max_documents"] == 5
    assert call_kwargs["get_extractive_answers"] is False


def _make_rag_builder(mock_retriever_class, mock_singleton, docs):
    """Helper to construct a Rag_Builder with fully mocked credentials."""
    mock_singleton.GOOGLE_APPLICATION_CREDENTIALS = "/fake/creds.json"
    mock_retriever_class.return_value.invoke.return_value = docs

    with (
        patch("pathlib.Path.open", MagicMock()),
        patch(
            "tenantfirstaid.langchain_tools.json.load",
            return_value={"type": "service_account"},
        ),
        patch(
            "tenantfirstaid.langchain_tools.service_account.Credentials.from_service_account_file"
        ),
    ):
        return Rag_Builder(filter='state: ANY("or")')


@patch("tenantfirstaid.langchain_tools.VertexAISearchRetriever")
@patch("tenantfirstaid.langchain_tools.SINGLETON")
def test_rag_builder_search_formats_multiple_results(
    mock_singleton, mock_retriever_class
):
    """Test that search() labels each result so the agent can distinguish them."""
    docs = [
        Document(page_content="first passage", metadata={"source": "ORS090.txt"}),
        Document(page_content="second passage", metadata={"source": "ORS090.txt"}),
    ]
    builder = _make_rag_builder(mock_retriever_class, mock_singleton, docs)
    result = builder.search("late fees")

    assert "[Result 1]" in result
    assert "[Result 2]" in result
    assert "first passage" in result
    assert "second passage" in result
    # Results should be double-newline separated, not run together.
    assert result.index("first passage") < result.index("second passage")


@patch("tenantfirstaid.langchain_tools.VertexAISearchRetriever")
@patch("tenantfirstaid.langchain_tools.SINGLETON")
def test_rag_builder_search_returns_empty_string_when_no_docs(
    mock_singleton, mock_retriever_class
):
    """Test that search() returns empty string when retriever finds nothing."""
    builder = _make_rag_builder(mock_retriever_class, mock_singleton, [])
    assert builder.search("late fees") == ""


@patch("tenantfirstaid.langchain_tools.VertexAISearchRetriever")
@patch("tenantfirstaid.langchain_tools.SINGLETON")
def test_rag_builder_search_handles_grpc_error(mock_singleton, mock_retriever_class):
    """Test that a gRPC error returns a user-friendly message instead of raising."""
    builder = _make_rag_builder(mock_retriever_class, mock_singleton, [])
    builder.rag.invoke = MagicMock(side_effect=grpc.RpcError("502:Bad Gateway"))

    result = builder.search("late fees")

    assert "temporarily unavailable" in result


def test_tool_schema_matches_function_signature():
    """Test that Pydantic schema matches function defaults."""
    schema_fields = set(CityStateLawsInputSchema.model_fields.keys())
    func_params = set(
        inspect.signature(retrieve_city_state_laws.func).parameters.keys()  # type: ignore[unresolved-attribute]
    )
    func_params.discard("runtime")

    assert schema_fields == func_params
