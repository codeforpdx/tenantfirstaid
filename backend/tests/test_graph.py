"""Tests for graph.py — agent graph factory and middleware."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from tenantfirstaid.graph import (
    TFAContext,
    _adapt_query,
    _DatasetInput,
    _SystemPromptFromContext,
    create_graph,
    prepare_system_prompt,
)
from tenantfirstaid.location import OregonCity, UsaState

pytestmark = pytest.mark.langchain


@pytest.fixture
def oregon_state():
    return UsaState.from_maybe_str("or")


@pytest.fixture
def portland_city():
    return OregonCity.from_maybe_str("Portland")


@patch("tenantfirstaid.graph._get_llm")
def test_create_graph_with_system_prompt(mock_llm, oregon_state, portland_city):
    """Web-app path: passing a system prompt produces a compiled graph."""
    mock_llm.return_value = MagicMock()
    prompt = prepare_system_prompt(portland_city, oregon_state)
    graph = create_graph(system_prompt=prompt)
    assert graph is not None


@patch("tenantfirstaid.graph._get_llm")
def test_create_graph_without_system_prompt(mock_llm):
    """LangGraph deployment path: no system prompt uses middleware instead."""
    mock_llm.return_value = MagicMock()
    graph = create_graph()
    assert graph is not None


@patch("tenantfirstaid.graph._get_llm")
def test_graph_factory(mock_llm):
    """The module-level graph() factory returns a compiled graph."""
    mock_llm.return_value = MagicMock()
    from tenantfirstaid.graph import graph

    result = graph()
    assert result is not None


def test_adapt_query_converts_query_to_human_message():
    """_adapt_query wraps a bare query string in a HumanMessage."""
    state: _DatasetInput = {
        "query": "What are my rights?",
        "state": UsaState.OREGON,
        "messages": [],
    }
    result = _adapt_query(state)
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "What are my rights?"


def test_adapt_query_no_op_when_messages_present():
    """_adapt_query leaves state unchanged when messages already exist."""
    existing = HumanMessage(content="existing message")
    state: _DatasetInput = {
        "query": "ignored",
        "state": UsaState.OREGON,
        "messages": [existing],
    }
    result = _adapt_query(state)
    assert result == {}


def test_adapt_query_no_op_when_no_query():
    """_adapt_query returns nothing when query is absent."""
    state: _DatasetInput = {"state": UsaState.OREGON, "messages": []}
    result = _adapt_query(state)
    assert result == {}


def _make_middleware_request(
    prompt: str, city: str | None = None, state: str | None = None
) -> MagicMock:
    """Build a minimal ModelRequest-like object for middleware tests."""
    request = MagicMock()
    request.runtime.context = TFAContext(system_prompt=prompt)
    request.state = {"city": city, "state": state}
    request.system_message = None
    # override() must return a new mock whose system_message reflects the kwarg,
    # mirroring the real ModelRequest.override() behaviour.
    def _override(**kwargs):
        child = MagicMock()
        child.runtime = request.runtime
        child.state = request.state
        for k, v in kwargs.items():
            setattr(child, k, v)
        return child
    request.override = _override
    return request


def test_middleware_injects_location_from_state():
    """Middleware appends city/state from agent state to the system prompt."""
    middleware = _SystemPromptFromContext()
    request = _make_middleware_request("Base prompt.", city="Portland", state="OR")

    forwarded = []
    handler = MagicMock(side_effect=lambda r: forwarded.append(r) or MagicMock())
    middleware.wrap_model_call(request, handler)

    injected = forwarded[0].system_message
    assert isinstance(injected, SystemMessage)
    assert "Portland OR" in injected.content
    assert "Base prompt." in injected.content


def test_middleware_without_city():
    """Middleware works when city is None (state-only location)."""
    middleware = _SystemPromptFromContext()
    request = _make_middleware_request("Base prompt.", city=None, state="OR")

    forwarded = []
    handler = MagicMock(side_effect=lambda r: forwarded.append(r) or MagicMock())
    middleware.wrap_model_call(request, handler)

    injected = forwarded[0].system_message
    assert "OR" in injected.content
    # No leading space before state when city is absent.
    assert "The user is in OR." in injected.content


def test_middleware_uses_custom_prompt_from_context():
    """Middleware uses the prompt from Studio context, not the default."""
    middleware = _SystemPromptFromContext()
    custom = "You are a custom agent."
    request = _make_middleware_request(custom, state="OR")

    forwarded = []
    handler = MagicMock(side_effect=lambda r: forwarded.append(r) or MagicMock())
    middleware.wrap_model_call(request, handler)

    assert custom in forwarded[0].system_message.content


@pytest.mark.asyncio
async def test_middleware_async_injects_location():
    """Async middleware path also reads city/state from agent state."""
    middleware = _SystemPromptFromContext()
    request = _make_middleware_request("Async base.", city="Eugene", state="OR")

    forwarded = []

    async def async_handler(req):
        forwarded.append(req)
        return MagicMock()

    await middleware.awrap_model_call(request, async_handler)

    injected = forwarded[0].system_message
    assert isinstance(injected, SystemMessage)
    assert "Eugene OR" in injected.content


@patch("tenantfirstaid.graph._get_llm")
def test_graph_adapter_converts_query_to_human_message(mock_get_llm):
    """E2E: query input flows through the adapt node and reaches the agent as a HumanMessage.

    Runs the full wrapper graph (adapt → agent) with a mocked LLM, then
    asserts the final state contains the HumanMessage that adapt produced.
    """
    from langchain_core.messages import AIMessage, AIMessageChunk

    from tenantfirstaid.graph import graph

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    # The agent framework may call invoke or stream on the bound LLM; both
    # must return real message objects (not MagicMock) so LangChain can
    # coerce them. No tool_calls means the agent stops after one round.
    canned_response = AIMessageChunk(content="You have rights.")
    mock_llm.invoke.return_value = AIMessage(content="You have rights.")
    mock_llm.stream.return_value = iter([canned_response])
    mock_get_llm.return_value = mock_llm

    g = graph()
    result = g.invoke(
        {"query": "Can my landlord enter without notice?", "state": "or"},
        config={"configurable": {"thread_id": "test-e2e"}},
        context=TFAContext(),
    )

    human_messages = [m for m in result.get("messages", []) if isinstance(m, HumanMessage)]
    assert len(human_messages) == 1
    assert human_messages[0].content == "Can my landlord enter without notice?"
