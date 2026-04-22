"""Tests for LangChain-based chat manager."""

from unittest.mock import MagicMock, patch

import httpcore
import httpx
import pytest
from langchain_core.messages import AIMessage

from tenantfirstaid.graph import prepare_system_prompt, tools
from tenantfirstaid.langchain_chat_manager import LangChainChatManager
from tenantfirstaid.location import OregonCity, UsaState

pytestmark = pytest.mark.langchain


@pytest.fixture
def oregon_state():
    return UsaState.from_maybe_str("or")


@pytest.fixture
def portland_city():
    return OregonCity.from_maybe_str("Portland")


@pytest.fixture
def eugene_city():
    return OregonCity.from_maybe_str("Eugene")


def test_system_prompt_includes_location(oregon_state, portland_city):
    """Test that system prompt includes user location."""
    prompt = prepare_system_prompt(portland_city, oregon_state)

    assert "Portland OR" in prompt.content


def test_prepare_system_prompt_includes_city_state(oregon_state, portland_city):
    prompt = prepare_system_prompt(portland_city, oregon_state)
    assert (
        f"The user is in {portland_city.capitalize()} {oregon_state.upper()}."
        in prompt.content
    )


def test_tools_include_rag_retrieval():
    """Test that tools list includes RAG retrieval and letter template tools."""
    assert len(tools) == 3
    tool_names = [tool.name for tool in tools]
    assert "retrieve_city_state_laws" in tool_names
    assert "generate_letter" in tool_names
    assert "get_letter_template" in tool_names


def test_system_prompt_no_city(oregon_state):
    """When no city is provided, the location line should mention state only."""
    prompt = prepare_system_prompt(None, oregon_state)
    assert "The user is in" in prompt.content
    assert "OR" in prompt.content


def test_system_prompt_state_only():
    state = UsaState.from_maybe_str("other")
    prompt = prepare_system_prompt(None, state)
    assert "OTHER" in prompt.content


@patch.object(LangChainChatManager, "_LangChainChatManager__create_agent_for_session")
def test_streaming_text_response(mock_create_agent, oregon_state, portland_city):
    mock_agent = MagicMock()
    ai_msg = AIMessage(content=[{"type": "text", "text": "You have rights."}])
    mock_agent.stream.return_value = iter(
        [("updates", {"agent": {"messages": [ai_msg]}})]
    )
    mock_create_agent.return_value = mock_agent

    cm = LangChainChatManager()
    blocks = list(
        cm.generate_streaming_response(
            messages=[{"role": "human", "content": "Help"}],
            city=portland_city,
            state=oregon_state,
            thread_id=None,
        )
    )
    assert any(b["type"] == "text" for b in blocks)


@patch.object(LangChainChatManager, "_LangChainChatManager__create_agent_for_session")
def test_streaming_custom_chunk_yields_non_standard_block(
    mock_create_agent, oregon_state
):
    """Custom-mode chunks (e.g. from generate_letter) are wrapped in NonStandardContentBlock so _classify_blocks can distinguish tool chunks from LLM chunks."""
    mock_agent = MagicMock()
    mock_agent.stream.return_value = iter(
        [("custom", {"type": "letter", "content": "Dear Landlord,"})]
    )
    mock_create_agent.return_value = mock_agent

    cm = LangChainChatManager()
    blocks = list(
        cm.generate_streaming_response(
            messages=[], city=None, state=oregon_state, thread_id=None
        )
    )

    assert len(blocks) == 1
    block = blocks[0]
    assert block["type"] == "non_standard"
    assert block["value"]["type"] == "letter"
    assert block["value"]["content"] == "Dear Landlord,"


@patch.object(LangChainChatManager, "_LangChainChatManager__create_agent_for_session")
def test_streaming_empty_chunk_skipped(mock_create_agent, oregon_state):
    mock_agent = MagicMock()
    mock_agent.stream.return_value = iter([("updates", {})])
    mock_create_agent.return_value = mock_agent

    cm = LangChainChatManager()
    blocks = list(
        cm.generate_streaming_response(
            messages=[], city=None, state=oregon_state, thread_id=None
        )
    )
    assert blocks == []


# ── stream retry logic ─────────────────────────────────────────────────────────

_STREAM_ONCE = "_LangChainChatManager__stream_once"
_GOOD_CHUNK: dict = {"type": "text", "text": "ok"}


def _good_stream(*_args, **_kwargs):
    yield _GOOD_CHUNK


@patch("tenantfirstaid.langchain_chat_manager.time.sleep")
@patch.object(LangChainChatManager, _STREAM_ONCE)
def test_retry_succeeds_on_second_attempt(mock_stream_once, mock_sleep, oregon_state):
    """First call raises a transient error; second succeeds and yields the chunk."""
    mock_stream_once.side_effect = [
        httpcore.ReadError("reset"),
        _good_stream(),
    ]
    cm = LangChainChatManager()
    blocks = list(
        cm.generate_streaming_response(
            messages=[], city=None, state=oregon_state, thread_id=None
        )
    )
    assert blocks == [_GOOD_CHUNK]
    assert mock_stream_once.call_count == 2
    mock_sleep.assert_called_once()


@patch("tenantfirstaid.langchain_chat_manager.time.sleep")
@patch.object(LangChainChatManager, _STREAM_ONCE)
def test_no_retry_after_partial_yield(mock_stream_once, mock_sleep, oregon_state):
    """If bytes were already sent to the client, re-raise immediately — no retry."""

    def _partial_then_error(*_args, **_kwargs):
        yield _GOOD_CHUNK
        raise httpcore.ReadError("mid-stream reset")

    mock_stream_once.return_value = _partial_then_error()
    cm = LangChainChatManager()
    with pytest.raises(httpcore.ReadError):
        list(
            cm.generate_streaming_response(
                messages=[], city=None, state=oregon_state, thread_id=None
            )
        )
    assert mock_stream_once.call_count == 1
    mock_sleep.assert_not_called()


@patch("tenantfirstaid.langchain_chat_manager.time.sleep")
@patch.object(LangChainChatManager, _STREAM_ONCE)
def test_raises_after_max_retries_exhausted(
    mock_stream_once, _mock_sleep, oregon_state
):
    """After _MAX_STREAM_RETRIES transient failures, the error propagates."""
    cm = LangChainChatManager()
    total_attempts = cm._MAX_STREAM_RETRIES + 1
    mock_stream_once.side_effect = [httpx.ReadError("reset")] * total_attempts
    with pytest.raises(httpx.ReadError):
        list(
            cm.generate_streaming_response(
                messages=[], city=None, state=oregon_state, thread_id=None
            )
        )
    assert mock_stream_once.call_count == total_attempts


@patch.object(LangChainChatManager, _STREAM_ONCE)
def test_non_retryable_exception_propagates_immediately(mock_stream_once, oregon_state):
    """ValueError and similar errors are not caught and don't trigger a retry."""
    mock_stream_once.side_effect = ValueError("bad input")
    cm = LangChainChatManager()
    with pytest.raises(ValueError):
        list(
            cm.generate_streaming_response(
                messages=[], city=None, state=oregon_state, thread_id=None
            )
        )
    assert mock_stream_once.call_count == 1


@patch("tenantfirstaid.langchain_chat_manager.time.sleep")
@patch.object(LangChainChatManager, _STREAM_ONCE)
def test_retry_restores_messages(mock_stream_once, _mock_sleep, oregon_state):
    """Message list is restored to its pre-attempt state before each retry."""
    original: list = [{"role": "human", "content": "Help"}]
    msgs: list = list(original)
    mock_stream_once.side_effect = [ConnectionError("reset"), _good_stream()]
    cm = LangChainChatManager()
    list(
        cm.generate_streaming_response(
            messages=msgs, city=None, state=oregon_state, thread_id=None
        )
    )
    # After the successful retry, messages should equal the original snapshot.
    assert msgs == original


@patch.object(LangChainChatManager, _STREAM_ONCE)
def test_all_transient_error_types_trigger_retry(mock_stream_once, oregon_state):
    """httpcore.ReadError, httpx.ReadError, and ConnectionError all retry."""
    for exc_type in (httpcore.ReadError, httpx.ReadError, ConnectionError):
        mock_stream_once.side_effect = [exc_type("reset"), _good_stream()]
        cm = LangChainChatManager()
        with patch("tenantfirstaid.langchain_chat_manager.time.sleep"):
            blocks = list(
                cm.generate_streaming_response(
                    messages=[], city=None, state=oregon_state, thread_id=None
                )
            )
        assert blocks == [_GOOD_CHUNK], f"{exc_type} did not trigger a retry"


@patch("tenantfirstaid.graph._get_llm")
def test_agent_creation_with_thread_id(mock_get_llm, oregon_state, portland_city):
    mock_get_llm.return_value = MagicMock()
    cm = LangChainChatManager()
    create = getattr(cm, "_LangChainChatManager__create_agent_for_session")
    agent = create(portland_city, oregon_state, "test-thread")
    assert agent is not None


@patch("tenantfirstaid.graph._get_llm")
def test_agent_creation_without_thread_id(mock_get_llm, oregon_state, portland_city):
    mock_get_llm.return_value = MagicMock()
    cm = LangChainChatManager()
    create = getattr(cm, "_LangChainChatManager__create_agent_for_session")
    agent = create(portland_city, oregon_state, None)
    assert agent is not None
