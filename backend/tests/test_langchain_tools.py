"""
Test location sanitization and other methods
"""

import json
import re
from datetime import date, datetime, time, timedelta
from typing import Dict, cast
from unittest.mock import MagicMock, patch

import httpx
import pytest
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from hypothesis import example, given
from hypothesis import strategies as st
from langchain_core.tools import StructuredTool

from tenantfirstaid.constants import DatastoreKey
from tenantfirstaid.google_auth import load_gcp_credentials
from tenantfirstaid.langchain_tools import (
    CityStateLawsInputSchema,
    NoticeServiceMethod,
    RagBuilder,
    _make_rag_tool,
    calculate_ors_90_160_notice_deadline,
    filter_builder,
    generate_letter,
    get_active_rag_tools,
    get_letter_template,
    repair_mojibake,
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


# --- repair_mojibake property tests ---


@pytest.mark.property
@given(st.text(alphabet=st.characters(max_codepoint=0x7F)))
def test_repair_mojibake_ascii_unchanged(text: str) -> None:
    """Pure ASCII text is returned unchanged — no mojibake to repair."""
    assert repair_mojibake(text) == text


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
    assert repair_mojibake(mojibake) == original


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
    assert repair_mojibake(text) == text


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
        query="test query",
        state=UsaState("or"),
        city=None,
        max_documents=3,
        max_extractive_segment_count=3,
    )
    mock_rag_class.assert_called_once_with(
        data_store_id="fake-id",
        name="test_tool",
        filter="custom-filter",
        max_documents=3,
        max_extractive_segment_count=3,
    )


def test_filter_builder_state_only():
    """Test filter with state only (no city) produces null city."""
    result = filter_builder(UsaState("or"), None)
    assert 'city: ANY("null")' in result
    assert 'state: ANY("or")' in result


def test_filter_builder_with_city():
    """Test filter with city includes state-level docs."""
    result = filter_builder(UsaState("or"), OregonCity("eugene"))
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
    mock_instance.invoke.side_effect = [
        httpx.ReadError("Connection reset by peer"),
        [mock_doc],
    ]

    builder = RagBuilder(
        data_store_id="fake-datastore-id",
        filter='city: ANY("null") AND state: ANY("or")',
    )
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

    builder = RagBuilder(
        data_store_id="fake-datastore-id",
        filter='city: ANY("null") AND state: ANY("or")',
    )
    with pytest.raises(httpx.ReadError):
        builder.search("test query")

    assert mock_instance.invoke.call_count == 3


# --- calculate_ors_90_160_notice_deadline tests ---


def _fmt(dt: datetime) -> str:
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")


def _extract_deadline(result: str) -> datetime:
    """Parse the DEADLINE line back into a datetime, for property tests that need
    to compare two computed deadlines rather than match a hardcoded string."""
    match = re.search(r"DEADLINE: (.+?)\. This deadline", result)
    assert match, f"no DEADLINE line found in result:\n{result}"
    return datetime.strptime(match.group(1), "%A, %B %d, %Y at %I:%M %p")


def test_notice_deadline_day_based_personal_delivery():
    """ORS 90.160(1): day of service excluded, last day counted through 11:59 PM."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 31, 23, 59))}" in result
    assert "ORS 90.160(1)" in result
    assert "90.155(2)" not in result


def test_notice_deadline_day_based_mail_alone_adds_three_days():
    """ORS 90.155(2): mail-alone service extends the minimum period by 3 days."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.FIRST_CLASS_MAIL,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 2, 3, 23, 59))}" in result
    assert "ORS 90.155(2)" in result


def test_notice_deadline_day_based_mail_alone_termination_still_extends():
    """ORS 90.155(2)'s extension applies to any notice "served by mail under
    subsection (1)(b)" with no termination-based carve-out — the extension must
    still apply when is_termination_notice=True, not just the False case the
    other mail-alone test covers."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.FIRST_CLASS_MAIL,
            "is_termination_notice": True,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 2, 3, 23, 59))}" in result
    assert "ORS 90.160(1) and ORS 90.155(2)" in result


def test_notice_deadline_hour_based_starts_immediately_on_service():
    """ORS 90.160(2)(a): hour clock starts immediately upon service."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "14:00",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 4, 14, 0))}" in result
    assert "ORS 90.160(2)(a)" in result


def test_notice_deadline_accepts_12_hour_service_time():
    """service_time also accepts 12-hour clock strings, as its own description
    promises (e.g. "2:30 PM"), not just 24-hour/ISO."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "2:00 PM",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 4, 14, 0))}" in result


def test_notice_deadline_hour_based_mail_alone_adds_three_days():
    """ORS 90.155(2)'s three-day mail extension applies to hour-based periods too,
    added on top of the hour count rather than replacing it."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "14:00",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.FIRST_CLASS_MAIL,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 7, 14, 0))}" in result
    assert "ORS 90.160(2)(a) and ORS 90.155(2)" in result


def test_notice_deadline_hour_based_mail_and_attach_termination_special_start():
    """ORS 90.160(2)(b): mail-and-attach termination notice starts the clock at
    11:59 PM on the day both methods completed, regardless of service_time."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.MAIL_AND_ATTACH,
            "is_termination_notice": True,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 4, 23, 59))}" in result
    assert "ORS 90.160(2)(b)" in result
    assert "rental agreement authorizes it" in result


def test_notice_deadline_hour_based_mail_and_attach_non_termination_needs_service_time():
    """The 90.160(2)(b) special start is for termination notices only — a
    non-termination mail-and-attach hour-based notice still needs service_time."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 24,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.MAIL_AND_ATTACH,
            "is_termination_notice": False,
        }
    )
    assert "MISSING INPUT" in result
    assert "DEADLINE:" not in result


def test_notice_deadline_hour_based_mail_and_attach_non_termination_full_deadline():
    """With service_time supplied, a non-termination mail-and-attach hour-based
    notice must use the ordinary ORS 90.160(2)(a) immediate start — no special
    11:59 PM start (that's termination-only) and no 90.155(2) extension (that's
    (1)(b)-alone-mail-only)."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "14:00",
            "period_value": 24,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.MAIL_AND_ATTACH,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 2, 14, 0))}" in result
    assert "ORS 90.160(2)(a)" in result
    assert "90.155(2)" not in result


def test_notice_deadline_hour_based_mail_and_attach_termination_ignores_given_service_time():
    """ORS 90.160(2)(b)'s clock start is 11:59 PM "regardless of what time service
    actually happened" — if a caller supplies service_time anyway, it must not
    change the computed deadline."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "03:00",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.MAIL_AND_ATTACH,
            "is_termination_notice": True,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 4, 23, 59))}" in result
    assert "ORS 90.160(2)(b)" in result


def test_notice_deadline_day_based_mail_and_attach_termination_no_special_start():
    """ORS 90.160(2)(b)'s 11:59 PM special start applies only to hour-based periods
    (90.160(2) itself is "for references... based on a number of hours") — a
    day-based termination notice served mail-and-attach gets plain ORS 90.160(1)
    day counting, no extension, no special start."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.MAIL_AND_ATTACH,
            "is_termination_notice": True,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 31, 23, 59))}" in result
    assert "ORS 90.160(1)" in result
    assert "90.160(2)(b)" not in result
    assert "90.155(2)" not in result


def test_notice_deadline_hour_based_missing_service_time():
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert "MISSING INPUT" in result
    assert "DEADLINE:" not in result


def test_notice_deadline_email_only_termination_is_rejected():
    """ORS 90.155(5): e-mail alone never validly serves a termination notice."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.EMAIL_ONLY,
            "is_termination_notice": True,
        }
    )
    assert "SERVICE INVALID" in result
    assert "DEADLINE:" not in result


def test_notice_deadline_email_and_mail_non_termination_treated_as_mail_service():
    """A non-termination notice sent by email_and_mail is ordinary ORS 90.155(1)(b)
    mail service with the e-mail copy as an ORS 90.155(3) alternative method — it
    must NOT be rejected, and it must still get the 90.155(2) three-day extension
    (rejecting it and forcing a retry with email_only silently drops that extension,
    giving the tenant a deadline three days earlier than the statute allows)."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.EMAIL_AND_MAIL,
            "is_termination_notice": False,
        }
    )
    assert "INPUT MISMATCH" not in result
    assert f"DEADLINE: {_fmt(datetime(2026, 2, 3, 23, 59))}" in result
    assert "ORS 90.160(1) and ORS 90.155(2)" in result
    assert "ORS 90.155(3) alternative method" in result


def test_notice_deadline_email_and_mail_termination_gets_special_start():
    """ORS 90.155(5): a termination notice sent by email_and_mail gets the
    ORS 90.160(2)(b) 11:59 PM clock start and no 90.155(2) extension — the only
    branch that produces a deadline for this service method+termination combo."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.EMAIL_AND_MAIL,
            "is_termination_notice": True,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 4, 23, 59))}" in result
    assert "ORS 90.160(2)(b)" in result
    assert "ORS 90.155(2)" not in result


def test_notice_deadline_day_based_email_and_mail_termination_no_extension():
    """Same hours-only scoping as mail-and-attach: a day-based termination notice
    sent by email_and_mail gets plain ORS 90.160(1) counting, no 90.160(2)(b)
    special start and no 90.155(2) extension (that extension is (1)(b)-mail-alone
    only, and (5) is a separate, non-extended service method)."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.EMAIL_AND_MAIL,
            "is_termination_notice": True,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 31, 23, 59))}" in result
    assert "ORS 90.160(1)" in result
    assert "90.160(2)(b)" not in result
    assert "90.155(2)" not in result


def test_notice_deadline_hour_based_email_and_mail_non_termination_adds_three_days():
    """The High-severity fix (email_and_mail non-termination treated as ordinary
    mail service) must hold in the hour-based branch too, not just day-based —
    it's a separate code path with its own arithmetic."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "14:00",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.EMAIL_AND_MAIL,
            "is_termination_notice": False,
        }
    )
    assert f"DEADLINE: {_fmt(datetime(2026, 1, 7, 14, 0))}" in result
    assert "ORS 90.160(2)(a) and ORS 90.155(2)" in result


def test_notice_deadline_email_only_caveat_present():
    """The signed-addendum caveat must appear for email_only, not just mail_and_attach."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.EMAIL_ONLY,
            "is_termination_notice": False,
        }
    )
    assert "signed ORS 90.155(1)(d) addendum" in result


def test_notice_deadline_is_termination_notice_is_required():
    """is_termination_notice must never silently default — omitting it is a
    ValidationError, not a guess."""
    with pytest.raises(ValueError, match="is_termination_notice"):
        calculate_ors_90_160_notice_deadline.invoke(
            {
                "service_date": "2026-01-01",
                "period_value": 30,
                "period_unit": "days",
                "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            }
        )


def test_notice_deadline_output_separates_agent_notes_from_tenant_answer():
    """The AGENT NOTES section (UNIT CHECK, echoed inputs) must be clearly separated
    from the TENANT-FACING ANSWER section, so relaying "the output" verbatim can't
    leak agent-directed scaffolding to the tenant."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert "=== AGENT NOTES" in result
    assert "=== TENANT-FACING ANSWER" in result
    agent_section, tenant_section = result.split("=== TENANT-FACING ANSWER", 1)
    assert "UNIT CHECK" in agent_section
    assert "UNIT CHECK" not in tenant_section
    assert "DEADLINE:" in tenant_section
    assert "DEADLINE:" not in agent_section


def test_notice_deadline_unit_check_states_both_units_unambiguously():
    """The result must spell out that the period is hours, not days (or vice versa),
    so the model can't relay the wrong unit to the tenant."""
    days_result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert "30 DAYS, NOT 30 HOURS" in days_result

    hours_result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "09:00",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert "72 HOURS, NOT 72 DAYS" in hours_result


def test_notice_deadline_weekend_holiday_note_present():
    """ORS 90.160 explicitly overrides ORCP 10 — no weekend/holiday roll-forward."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
            "is_termination_notice": False,
        }
    )
    assert "NOT extended for weekends or holidays" in result


# --- exhaustive service_method x is_termination_notice coverage ---
#
# service_method (5) x is_termination_notice (2) x period_unit (2) = 20 combinations.
# Small enough to enumerate directly rather than rely on hand-picked examples to
# happen to cover every branch — split into a days table and an hours table since
# the two branches take structurally different inputs (hours needs service_time).
# Each row's (basis, deadline) was hand-computed against ORS 90.155/90.160 and cross-
# checked by invoking the tool directly before being written down here.

_DAYS_CASES = [
    (NoticeServiceMethod.PERSONAL_DELIVERY, False, "ORS 90.160(1)", date(2026, 1, 31)),
    (NoticeServiceMethod.PERSONAL_DELIVERY, True, "ORS 90.160(1)", date(2026, 1, 31)),
    (
        NoticeServiceMethod.FIRST_CLASS_MAIL,
        False,
        "ORS 90.160(1) and ORS 90.155(2)",
        date(2026, 2, 3),
    ),
    (
        NoticeServiceMethod.FIRST_CLASS_MAIL,
        True,
        "ORS 90.160(1) and ORS 90.155(2)",
        date(2026, 2, 3),
    ),
    (NoticeServiceMethod.MAIL_AND_ATTACH, False, "ORS 90.160(1)", date(2026, 1, 31)),
    (NoticeServiceMethod.MAIL_AND_ATTACH, True, "ORS 90.160(1)", date(2026, 1, 31)),
    (
        NoticeServiceMethod.EMAIL_AND_MAIL,
        False,
        "ORS 90.160(1) and ORS 90.155(2)",
        date(2026, 2, 3),
    ),
    (NoticeServiceMethod.EMAIL_AND_MAIL, True, "ORS 90.160(1)", date(2026, 1, 31)),
    (NoticeServiceMethod.EMAIL_ONLY, False, "ORS 90.160(1)", date(2026, 1, 31)),
    (NoticeServiceMethod.EMAIL_ONLY, True, None, None),  # rejected: SERVICE INVALID
]


@pytest.mark.parametrize(
    "service_method,is_termination_notice,basis,deadline_date",
    _DAYS_CASES,
    ids=[f"{m.value}-term={t}" for m, t, _, _ in _DAYS_CASES],
)
def test_notice_deadline_exhaustive_days(
    service_method, is_termination_notice, basis, deadline_date
):
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "period_value": 30,
            "period_unit": "days",
            "service_method": service_method,
            "is_termination_notice": is_termination_notice,
        }
    )
    if basis is None:
        assert "SERVICE INVALID" in result
        assert "DEADLINE:" not in result
    else:
        assert (
            f"DEADLINE: {_fmt(datetime.combine(deadline_date, time(23, 59)))}" in result
        )
        assert basis in result


_HOURS_CASES = [
    (
        NoticeServiceMethod.PERSONAL_DELIVERY,
        False,
        "ORS 90.160(2)(a)",
        datetime(2026, 1, 4, 14, 0),
    ),
    (
        NoticeServiceMethod.PERSONAL_DELIVERY,
        True,
        "ORS 90.160(2)(a)",
        datetime(2026, 1, 4, 14, 0),
    ),
    (
        NoticeServiceMethod.FIRST_CLASS_MAIL,
        False,
        "ORS 90.160(2)(a) and ORS 90.155(2)",
        datetime(2026, 1, 7, 14, 0),
    ),
    (
        NoticeServiceMethod.FIRST_CLASS_MAIL,
        True,
        "ORS 90.160(2)(a) and ORS 90.155(2)",
        datetime(2026, 1, 7, 14, 0),
    ),
    (
        NoticeServiceMethod.MAIL_AND_ATTACH,
        False,
        "ORS 90.160(2)(a)",
        datetime(2026, 1, 4, 14, 0),
    ),
    (
        NoticeServiceMethod.MAIL_AND_ATTACH,
        True,
        "ORS 90.160(2)(b)",
        datetime(2026, 1, 4, 23, 59),
    ),
    (
        NoticeServiceMethod.EMAIL_AND_MAIL,
        False,
        "ORS 90.160(2)(a) and ORS 90.155(2)",
        datetime(2026, 1, 7, 14, 0),
    ),
    (
        NoticeServiceMethod.EMAIL_AND_MAIL,
        True,
        "ORS 90.160(2)(b)",
        datetime(2026, 1, 4, 23, 59),
    ),
    (
        NoticeServiceMethod.EMAIL_ONLY,
        False,
        "ORS 90.160(2)(a)",
        datetime(2026, 1, 4, 14, 0),
    ),
    (NoticeServiceMethod.EMAIL_ONLY, True, None, None),  # rejected: SERVICE INVALID
]


@pytest.mark.parametrize(
    "service_method,is_termination_notice,basis,deadline",
    _HOURS_CASES,
    ids=[f"{m.value}-term={t}" for m, t, _, _ in _HOURS_CASES],
)
def test_notice_deadline_exhaustive_hours(
    service_method, is_termination_notice, basis, deadline
):
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-01-01",
            "service_time": "14:00",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": service_method,
            "is_termination_notice": is_termination_notice,
        }
    )
    if basis is None:
        assert "SERVICE INVALID" in result
        assert "DEADLINE:" not in result
    else:
        assert f"DEADLINE: {_fmt(deadline)}" in result
        assert basis in result


# --- property-based tests ---
#
# The exhaustive tests above lock down which of the 20 discrete (service_method,
# is_termination_notice, period_unit) combinations takes which branch. These
# instead check invariants that must hold across the *continuous* inputs
# (service_date, period_value, service_time) — date/leap-year/month-boundary
# arithmetic that a handful of hand-picked examples (mostly anchored on
# 2026-01-01) wouldn't exercise.

_VALID_METHOD_TERMINATION_PAIRS = [
    (m, t)
    for m in NoticeServiceMethod
    for t in (False, True)
    if not (m == NoticeServiceMethod.EMAIL_ONLY and t)
]

_EXTENSION_METHOD_TERMINATION_PAIRS = [
    (NoticeServiceMethod.FIRST_CLASS_MAIL, False),
    (NoticeServiceMethod.FIRST_CLASS_MAIL, True),
    (NoticeServiceMethod.EMAIL_AND_MAIL, False),
]

_NO_EXTENSION_METHOD_TERMINATION_UNITS = [
    (NoticeServiceMethod.MAIL_AND_ATTACH, False, "days"),
    (NoticeServiceMethod.MAIL_AND_ATTACH, False, "hours"),
    (NoticeServiceMethod.MAIL_AND_ATTACH, True, "days"),
    (NoticeServiceMethod.EMAIL_AND_MAIL, True, "days"),
    (NoticeServiceMethod.EMAIL_ONLY, False, "days"),
    (NoticeServiceMethod.EMAIL_ONLY, False, "hours"),
]


@pytest.mark.property
@given(
    service_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    period_value=st.integers(min_value=1, max_value=500),
    period_unit=st.sampled_from(["days", "hours"]),
    service_time=st.times().map(lambda t: t.replace(second=0, microsecond=0)),
    method_and_termination=st.sampled_from(_EXTENSION_METHOD_TERMINATION_PAIRS),
)
@example(
    service_date=date(2024, 2, 29),
    period_value=30,
    period_unit="days",
    service_time=time(14, 0),
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
@example(
    service_date=date(2024, 12, 31),
    period_value=30,
    period_unit="days",
    service_time=time(14, 0),
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
@example(
    service_date=date(2026, 3, 8),
    period_value=72,
    period_unit="hours",
    service_time=time(14, 0),
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
@example(
    service_date=date(2026, 11, 1),
    period_value=72,
    period_unit="hours",
    service_time=time(14, 0),
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
def test_notice_deadline_mail_extension_always_adds_exactly_three_days(
    service_date, period_value, period_unit, service_time, method_and_termination
):
    """ORS 90.155(2)'s three-day extension is unconditional given (1)(b) mail
    service — switching only service_method from personal_delivery to an
    extension-getting method must shift the deadline by exactly +3 days for
    every extension-getting (service_method, is_termination_notice)
    combination, including the email-and-mail non-termination path, and for
    any date/period combination, not just the hand-picked 2026-01-01
    examples."""
    service_method, is_termination_notice = method_and_termination
    kwargs = {
        "service_date": service_date.isoformat(),
        "period_value": period_value,
        "period_unit": period_unit,
        "is_termination_notice": is_termination_notice,
    }
    if period_unit == "hours":
        kwargs["service_time"] = service_time.isoformat()

    base = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "service_method": NoticeServiceMethod.PERSONAL_DELIVERY}
    )
    extension = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "service_method": service_method}
    )
    assert _extract_deadline(extension) - _extract_deadline(base) == timedelta(days=3)


@pytest.mark.property
@given(
    service_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    period_value=st.integers(min_value=1, max_value=500),
    service_method=st.sampled_from(
        [NoticeServiceMethod.MAIL_AND_ATTACH, NoticeServiceMethod.EMAIL_AND_MAIL]
    ),
    time_a=st.times().map(lambda t: t.replace(second=0, microsecond=0)),
    time_b=st.times().map(lambda t: t.replace(second=0, microsecond=0)),
)
@example(
    service_date=date(2024, 2, 29),
    period_value=72,
    service_method=NoticeServiceMethod.MAIL_AND_ATTACH,
    time_a=time(9, 0),
    time_b=time(17, 30),
)
@example(
    service_date=date(2024, 12, 31),
    period_value=72,
    service_method=NoticeServiceMethod.MAIL_AND_ATTACH,
    time_a=time(9, 0),
    time_b=time(17, 30),
)
@example(
    service_date=date(2026, 3, 8),
    period_value=72,
    service_method=NoticeServiceMethod.MAIL_AND_ATTACH,
    time_a=time(9, 0),
    time_b=time(17, 30),
)
@example(
    service_date=date(2026, 11, 1),
    period_value=72,
    service_method=NoticeServiceMethod.MAIL_AND_ATTACH,
    time_a=time(9, 0),
    time_b=time(17, 30),
)
def test_notice_deadline_special_start_ignores_service_time(
    service_date, period_value, service_method, time_a, time_b
):
    """ORS 90.160(2)(b)'s clock start is 11:59 PM "regardless of what time service
    actually happened" — for any termination notice served mail-and-attach or
    email-and-mail, the computed deadline must not depend on the service_time
    value at all, across the whole time domain, not just one example pair."""
    kwargs = {
        "service_date": service_date.isoformat(),
        "period_value": period_value,
        "period_unit": "hours",
        "service_method": service_method,
        "is_termination_notice": True,
    }
    result_a = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "service_time": time_a.isoformat()}
    )
    result_b = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "service_time": time_b.isoformat()}
    )
    assert _extract_deadline(result_a) == _extract_deadline(result_b)


@pytest.mark.property
@given(
    service_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    period_value=st.integers(min_value=1, max_value=500),
    method_and_termination=st.sampled_from(_VALID_METHOD_TERMINATION_PAIRS),
)
@example(
    service_date=date(2024, 2, 29),
    period_value=30,
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
@example(
    service_date=date(2024, 12, 31),
    period_value=30,
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
@example(
    service_date=date(2026, 3, 8),
    period_value=30,
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
@example(
    service_date=date(2026, 11, 1),
    period_value=30,
    method_and_termination=(NoticeServiceMethod.FIRST_CLASS_MAIL, False),
)
def test_notice_deadline_day_based_always_ends_at_2359(
    service_date, period_value, method_and_termination
):
    """ORS 90.160(1): a day-based deadline always runs through 11:59 PM of the
    last day, for any valid service_method/is_termination_notice/date/period
    combination — including leap-year and year-boundary crossings that the
    hand-picked 2026-01-01 examples don't reach."""
    service_method, is_termination_notice = method_and_termination
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": service_date.isoformat(),
            "period_value": period_value,
            "period_unit": "days",
            "service_method": service_method,
            "is_termination_notice": is_termination_notice,
        }
    )
    assert _extract_deadline(result).time() == time(23, 59)


@pytest.mark.property
@given(
    service_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    period_value=st.integers(min_value=1, max_value=500),
    period_unit=st.sampled_from(["days", "hours"]),
    method_and_termination=st.sampled_from(_VALID_METHOD_TERMINATION_PAIRS),
    service_time=st.times().map(lambda t: t.replace(second=0, microsecond=0)),
)
@example(
    service_date=date(2024, 2, 29),
    period_value=30,
    period_unit="days",
    method_and_termination=(NoticeServiceMethod.PERSONAL_DELIVERY, False),
    service_time=time(14, 0),
)
@example(
    service_date=date(2024, 12, 31),
    period_value=30,
    period_unit="days",
    method_and_termination=(NoticeServiceMethod.PERSONAL_DELIVERY, False),
    service_time=time(14, 0),
)
@example(
    service_date=date(2026, 3, 8),
    period_value=72,
    period_unit="hours",
    method_and_termination=(NoticeServiceMethod.MAIL_AND_ATTACH, True),
    service_time=time(14, 0),
)
@example(
    service_date=date(2026, 11, 1),
    period_value=72,
    period_unit="hours",
    method_and_termination=(NoticeServiceMethod.MAIL_AND_ATTACH, True),
    service_time=time(14, 0),
)
def test_notice_deadline_always_after_service(
    service_date, period_value, period_unit, method_and_termination, service_time
):
    """The computed deadline must never land at or before the moment of service,
    for any valid input combination — a basic sanity bound on the arithmetic."""
    service_method, is_termination_notice = method_and_termination
    kwargs = {
        "service_date": service_date.isoformat(),
        "period_value": period_value,
        "period_unit": period_unit,
        "service_method": service_method,
        "is_termination_notice": is_termination_notice,
    }
    if period_unit == "hours":
        kwargs["service_time"] = service_time.isoformat()
    else:
        service_time = time(0, 0)
    result = calculate_ors_90_160_notice_deadline.invoke(kwargs)
    assert _extract_deadline(result) > datetime.combine(service_date, service_time)


@pytest.mark.property
@given(
    service_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    period_value=st.integers(min_value=1, max_value=500),
    service_time=st.times().map(lambda t: t.replace(second=0, microsecond=0)),
    method_termination_unit=st.sampled_from(_NO_EXTENSION_METHOD_TERMINATION_UNITS),
)
def test_notice_deadline_non_extension_methods_match_personal_delivery(
    service_date, period_value, service_time, method_termination_unit
):
    """The ORS 90.155(2) extension must not leak into methods that don't qualify
    for it — every combination that gets neither an extension nor a special
    clock start must land at exactly the same deadline as personal delivery,
    at any date, previously pinned at one hardcoded date."""
    service_method, is_termination_notice, period_unit = method_termination_unit
    kwargs = {
        "service_date": service_date.isoformat(),
        "period_value": period_value,
        "period_unit": period_unit,
        "is_termination_notice": is_termination_notice,
    }
    if period_unit == "hours":
        kwargs["service_time"] = service_time.isoformat()

    base = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "service_method": NoticeServiceMethod.PERSONAL_DELIVERY}
    )
    other = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "service_method": service_method}
    )
    assert _extract_deadline(other) - _extract_deadline(base) == timedelta(0)


@pytest.mark.property
@given(
    service_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)),
    period_value=st.integers(min_value=1, max_value=500),
    bump=st.integers(min_value=1, max_value=100),
    period_unit=st.sampled_from(["days", "hours"]),
    method_and_termination=st.sampled_from(_VALID_METHOD_TERMINATION_PAIRS),
    service_time=st.times().map(lambda t: t.replace(second=0, microsecond=0)),
)
def test_notice_deadline_scales_linearly_with_period_value(
    service_date,
    period_value,
    bump,
    period_unit,
    method_and_termination,
    service_time,
):
    """Bumping period_value by N must shift the deadline by exactly N days or
    N hours (matching the period unit) for every method/termination/date/time
    combination — catches off-by-one and non-linear arithmetic that fixed
    period values wouldn't expose."""
    service_method, is_termination_notice = method_and_termination
    kwargs = {
        "service_date": service_date.isoformat(),
        "period_value": period_value,
        "period_unit": period_unit,
        "service_method": service_method,
        "is_termination_notice": is_termination_notice,
    }
    if period_unit == "hours":
        kwargs["service_time"] = service_time.isoformat()

    base = calculate_ors_90_160_notice_deadline.invoke(kwargs)
    bumped = calculate_ors_90_160_notice_deadline.invoke(
        {**kwargs, "period_value": period_value + bump}
    )
    expected_delta = (
        timedelta(days=bump) if period_unit == "days" else timedelta(hours=bump)
    )
    assert _extract_deadline(bumped) - _extract_deadline(base) == expected_delta


@pytest.mark.property
@given(period_value=st.integers(max_value=0))
def test_notice_deadline_rejects_non_positive_period_value(period_value):
    """The schema's gt=0 constraint on period_value must hold across the whole
    non-positive domain, not just at zero."""
    with pytest.raises(ValueError):
        calculate_ors_90_160_notice_deadline.invoke(
            {
                "service_date": "2026-01-01",
                "period_value": period_value,
                "period_unit": "days",
                "service_method": NoticeServiceMethod.PERSONAL_DELIVERY,
                "is_termination_notice": False,
            }
        )


def test_notice_deadline_missing_service_time_refusal_points_to_notice_text():
    """The missing-service-time refusal for an hour-based first-class-mail notice must direct the agent to the termination date and time the notice itself states under ORS 90.396(1), 90.398(1), 90.403(1) and 90.445(1), rather than asking the agent to guess or substitute a delivery time."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-03-02",
            "period_value": 72,
            "period_unit": "hours",
            "service_method": "first_class_mail",
            "is_termination_notice": False,
        }
    )
    assert result.startswith("MISSING INPUT, NO DEADLINE COMPUTED:")
    assert "90.396(1)" in result
    assert "Do NOT guess" in result
    assert "landlord mailed the notice" in result
    assert "11:59" not in result


def test_notice_deadline_caveat_and_note_render_on_separate_lines():
    """For a non-termination email_and_mail notice, the validity caveat and the first-class-mail note must render as separate labeled sections — the note must not sit under the "Caveat:" label where its "only valid if" framing would be misread as applying to the e-mail copy."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-03-02",
            "period_value": 30,
            "period_unit": "days",
            "service_method": "email_and_mail",
            "is_termination_notice": False,
        }
    )
    lines = result.splitlines()
    assert "Caveat:" in lines
    assert "Note:" in lines
    assert lines.index("Caveat:") < lines.index("Note:")
    assert (
        sum(
            1
            for line in lines
            if line.startswith("  - e-mail service is only valid if")
        )
        == 1
    )
    assert (
        sum(
            1
            for line in lines
            if line.startswith("  - this notice was served by first-class mail")
        )
        == 1
    )
    assert "addendum authorizes it; this notice" not in result


def test_notice_deadline_single_caveat_has_no_note_section():
    """A mail_and_attach notice with a single caveat and no note must render only the "Caveat:" section, with no empty "Note:" section."""
    result = calculate_ors_90_160_notice_deadline.invoke(
        {
            "service_date": "2026-03-02",
            "period_value": 30,
            "period_unit": "days",
            "service_method": "mail_and_attach",
            "is_termination_notice": False,
        }
    )
    lines = result.splitlines()
    assert "Caveat:" in lines
    assert "Note:" not in lines
    assert (
        sum(
            1
            for line in lines
            if line.startswith("  - mail-and-attach service is only valid if")
        )
        == 1
    )
