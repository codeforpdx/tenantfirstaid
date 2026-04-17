"""
Test location sanitization and other methods
"""

import json
from typing import Dict, cast
from unittest.mock import MagicMock, patch

import httpx
import pytest
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from hypothesis import given
from hypothesis import strategies as st
from langchain_core.tools import StructuredTool

from tenantfirstaid.constants import DatastoreKey
from tenantfirstaid.google_auth import load_gcp_credentials
from tenantfirstaid.langchain_tools import (
    CityStateLawsInputSchema,
    RagBuilder,
    _filter_builder,
    _make_rag_tool,
    _repair_mojibake,
    generate_letter,
    get_active_rag_tools,
    get_letter_template,
    retrieve_city_state_laws,
    retrieve_oregon_law_help,
)
from tenantfirstaid.location import OregonCity, UsaState

pytestmark = pytest.mark.langchain


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


@patch("tenantfirstaid.langchain_tools.get_stream_writer")
def test_generate_letter_writes_letter_chunk(mock_get_stream_writer):
    """Test that generate_letter emits a letter chunk via the stream writer."""
    mock_writer = MagicMock()
    mock_get_stream_writer.return_value = mock_writer

    letter_content = "Dear Landlord,\n\nPlease fix the heater.\n\nSincerely,\nTenant"
    result = generate_letter.invoke({"letter": letter_content})  # type: ignore[union-attr]

    mock_writer.assert_called_once_with({"type": "letter", "content": letter_content})
    assert result == "Letter generated successfully."


def test_get_letter_template_returns_template():
    """Test that get_letter_template returns the letter template content."""
    result = get_letter_template.invoke("")
    assert "[Your Name]" in result
    assert "ORS 90.320" in result


@patch("tenantfirstaid.langchain_tools.RagBuilder")
def test_retrieve_city_state_laws_state_only(mock_rag_class):
    """Test tool can be invoked with only state parameter."""
    mock_rag_class.return_value.search.return_value = ""

    # Should not raise despite city being omitted.
    retrieve_city_state_laws.invoke(  # type: ignore[union-attr]
        input={
            "query": "late rent fee",
            "state": UsaState("or"),
        },
    )


@patch("tenantfirstaid.langchain_tools.RagBuilder")
def test_retrieve_city_state_laws_with_city(mock_rag_class):
    """Test that city and state are forwarded to the filter."""
    mock_rag_class.return_value.search.return_value = ""

    retrieve_city_state_laws.invoke(  # type: ignore[union-attr]
        input={
            "query": "eviction notice",
            "city": OregonCity("portland"),
            "state": UsaState("or"),
        },
    )

    filter_arg = mock_rag_class.call_args[1]["filter"]
    assert "portland" in filter_arg and "or" in filter_arg


def test_tool_schema_matches_function_signature():
    """Test that retrieve_city_state_laws is bound to CityStateLawsInputSchema."""
    assert (
        cast(StructuredTool, retrieve_city_state_laws).args_schema
        is CityStateLawsInputSchema
    )


# --- _load_gcp_credentials tests ---

_AUTHORIZED_USER_JSON = json.dumps(
    {
        "type": "authorized_user",
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
        "refresh_token": "fake-refresh-token",
    }
)

_SERVICE_ACCOUNT_JSON = json.dumps(
    {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key_id": "fake-key-id",
        "private_key": "fake-key",
        "client_email": "fake@fake-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
)


def test_load_gcp_credentials_inline_authorized_user():
    """Inline JSON with type=authorized_user returns Credentials."""
    creds = load_gcp_credentials(_AUTHORIZED_USER_JSON)
    assert isinstance(creds, Credentials)


@patch.object(service_account.Credentials, "from_service_account_info")
def test_load_gcp_credentials_inline_service_account(mock_from_info):
    """Inline JSON with type=service_account calls the right factory."""
    mock_from_info.return_value = MagicMock(spec=service_account.Credentials)

    creds = load_gcp_credentials(_SERVICE_ACCOUNT_JSON)

    mock_from_info.assert_called_once()
    # Verify the parsed JSON was passed through.
    call_info = mock_from_info.call_args[0][0]
    assert call_info["type"] == "service_account"
    assert call_info["project_id"] == "fake-project"
    # Verify OAuth scopes are set (required for Vertex AI API).
    call_scopes = mock_from_info.call_args[1]["scopes"]
    assert "https://www.googleapis.com/auth/cloud-platform" in call_scopes
    assert isinstance(creds, service_account.Credentials)


def test_load_gcp_credentials_from_file(tmp_path):
    """File path containing authorized_user JSON returns Credentials."""
    cred_file = tmp_path / "creds.json"
    cred_file.write_text(_AUTHORIZED_USER_JSON)

    creds = load_gcp_credentials(str(cred_file))
    assert isinstance(creds, Credentials)


def test_load_gcp_credentials_unsupported_type():
    """Unsupported credential type raises ValueError."""
    bad_json = json.dumps({"type": "external_account", "audience": "test"})
    with pytest.raises(ValueError, match="Unsupported credential type"):
        load_gcp_credentials(bad_json)


def test_load_gcp_credentials_invalid_json():
    """Non-JSON string that isn't a file path raises."""
    with pytest.raises((json.JSONDecodeError, ValueError)):
        load_gcp_credentials("not-json-and-not-a-file")


@patch("tenantfirstaid.langchain_tools.RagBuilder")
def test_retrieve_city_state_laws_returns_joined_docs(mock_rag_class):
    """Test that RAG results are joined with newlines."""
    mock_rag_class.return_value.search.return_value = "Doc1 content\nDoc2 content"

    _func = getattr(retrieve_city_state_laws, "func")
    result = _func(
        query="eviction notice",
        state=UsaState("or"),
        city=OregonCity("portland"),
    )
    assert "Doc1 content" in result
    assert "Doc2 content" in result


# --- _repair_mojibake property tests ---


@pytest.mark.property
@given(st.text(alphabet=st.characters(max_codepoint=0x7F)))
def test_repair_mojibake_ascii_unchanged(text: str) -> None:
    """Pure ASCII text is returned unchanged — no mojibake to repair."""
    assert _repair_mojibake(text) == text


@pytest.mark.property
@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",))))
def test_repair_mojibake_repairs_genuine_mojibake(original: str) -> None:
    """Genuine mojibake (UTF-8 bytes misread as Latin-1) is fully repaired.

    Simulates the Vertex AI encoding defect: the original string's UTF-8
    bytes are misread as Latin-1, producing mojibake. The repair should
    recover the original string exactly.

    Surrogates (category Cs, U+D800–U+DFFF) are excluded because they cannot
    be encoded as UTF-8, so the test setup would raise UnicodeEncodeError
    before reaching the function under test.
    """
    mojibake = original.encode("utf-8").decode("latin-1")
    assert _repair_mojibake(mojibake) == original


@pytest.mark.property
@given(
    st.text(alphabet=st.characters(min_codepoint=0x80, max_codepoint=0xBF), min_size=1)
)
def test_repair_mojibake_continuation_byte_chars_unchanged(text: str) -> None:
    """Text with chars in U+0080–U+00BF is returned unchanged.

    These chars (including § U+00A7) encode to Latin-1 bytes 0x80–0xBF,
    which are UTF-8 continuation bytes. They can never form valid UTF-8
    without a preceding start byte, so the round-trip fails and the
    original text is returned as-is. This covers the Vertex AI defect
    where the leading 0xC2 byte of a UTF-8 § sequence is dropped.
    """
    assert _repair_mojibake(text) == text


@patch("tenantfirstaid.langchain_tools.RagBuilder")
def test_retrieve_city_state_laws_empty_results(mock_rag_class):
    """Test behavior when RAG returns no documents."""
    mock_rag_class.return_value.search.return_value = ""

    _func = getattr(retrieve_city_state_laws, "func")
    result = _func(
        query="obscure law",
        state=UsaState("or"),
    )
    assert result == ""


@patch("tenantfirstaid.langchain_tools.RagBuilder")
def test_retrieve_oregon_law_help_uses_correct_datastore(mock_rag_class):
    """Test that retrieve_oregon_law_help uses the oregon_law_help datastore without filtering."""
    mock_rag_class.return_value.search.return_value = "Some legal guidance"

    with patch.dict(
        "tenantfirstaid.langchain_tools.SINGLETON.VERTEX_AI_DATASTORES",
        {DatastoreKey.OREGON_LAW_HELP: "fake-olh-datastore-id"},
    ):
        _func = getattr(retrieve_oregon_law_help, "func")
        result = _func(query="eviction notice")

    mock_rag_class.assert_called_once_with(
        data_store_id="fake-olh-datastore-id",
        name="retrieve_oregon_law_help",
        filter=None,
        max_documents=3,
    )
    assert result == "Some legal guidance"


def test_get_active_rag_tools_filters_by_configured_datastores():
    """Tools whose datastore key is absent from env are excluded."""
    with patch.dict(
        "tenantfirstaid.langchain_tools.SINGLETON.VERTEX_AI_DATASTORES",
        {DatastoreKey.LAWS: "fake-laws-id"},
        clear=True,
    ):
        active = get_active_rag_tools()
    assert len(active) == 1
    assert active[0].name == "retrieve_city_state_laws"


@patch("tenantfirstaid.langchain_tools.RagBuilder")
def test_make_rag_tool_custom_filter_builder(mock_rag_class):
    """Custom filter_builder is called instead of the default."""
    mock_rag_class.return_value.search.return_value = ""
    custom_filter = MagicMock(return_value="custom-filter")

    custom_tool = _make_rag_tool(
        DatastoreKey.LAWS,
        "test_tool",
        "A test tool.",
        args_schema=CityStateLawsInputSchema,
        filter_builder=custom_filter,
    )

    with patch.dict(
        "tenantfirstaid.langchain_tools.SINGLETON.VERTEX_AI_DATASTORES",
        {DatastoreKey.LAWS: "fake-id"},
    ):
        _func = getattr(custom_tool, "func")
        _func(query="test query", state=UsaState("or"))

    custom_filter.assert_called_once_with(
        query="test query", state=UsaState("or"), city=None, max_documents=5
    )
    mock_rag_class.assert_called_once_with(
        data_store_id="fake-id",
        name="test_tool",
        filter="custom-filter",
        max_documents=5,
    )


def test_filter_builder_state_only():
    """Test filter with state only (no city) produces null city."""
    result = _filter_builder(UsaState("or"), None)
    assert 'city: ANY("null")' in result
    assert 'state: ANY("or")' in result


def test_filter_builder_with_city():
    """Test filter with city includes state-level docs."""
    result = _filter_builder(UsaState("or"), OregonCity("eugene"))
    assert 'city: ANY("eugene", "null")' in result
    assert 'state: ANY("or")' in result


@patch("tenantfirstaid.langchain_tools.get_stream_writer")
def test_generate_letter_empty_string(mock_get_stream_writer):
    """Test generate_letter with empty string."""
    mock_writer = MagicMock()
    mock_get_stream_writer.return_value = mock_writer

    _func = getattr(generate_letter, "func")
    result = _func(letter="")
    mock_writer.assert_called_once_with({"type": "letter", "content": ""})
    assert result == "Letter generated successfully."


# --- RagBuilder.search retry tests ---


@patch("tenantfirstaid.langchain_tools.load_gcp_credentials")
@patch("tenantfirstaid.langchain_tools.VertexAISearchRetriever")
def test_rag_search_retries_on_httpx_read_error(mock_retriever_class, mock_creds):
    """Transient httpx.ReadError is retried and succeeds on second attempt."""
    mock_creds.return_value = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "result text"

    mock_instance = mock_retriever_class.return_value
    mock_instance.invoke.side_effect = [httpx.ReadError("Connection reset by peer"), [mock_doc]]

    builder = RagBuilder(filter='city: ANY("null") AND state: ANY("or")')
    result = builder.search("test query")

    assert result == "result text"
    assert mock_instance.invoke.call_count == 2


@patch("tenantfirstaid.langchain_tools.load_gcp_credentials")
@patch("tenantfirstaid.langchain_tools.VertexAISearchRetriever")
def test_rag_search_gives_up_after_three_attempts(mock_retriever_class, mock_creds):
    """After 3 failed attempts the error is reraised."""
    mock_creds.return_value = MagicMock()

    mock_instance = mock_retriever_class.return_value
    mock_instance.invoke.side_effect = httpx.ReadError("Connection reset by peer")

    builder = RagBuilder(filter='city: ANY("null") AND state: ANY("or")')
    with pytest.raises(httpx.ReadError):
        builder.search("test query")

    assert mock_instance.invoke.call_count == 3
