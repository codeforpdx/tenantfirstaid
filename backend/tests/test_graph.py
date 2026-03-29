"""Tests for graph.py — agent graph factory and middleware."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import SystemMessage

from langchain_core.messages import HumanMessage

from tenantfirstaid.graph import (
    TFAContext,
    _DatasetInput,
    _SystemPromptFromContext,
    _adapt_query,
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
    state: _DatasetInput = {"query": "What are my rights?", "state": "or", "messages": []}  # type: ignore[typeddict-item]
    result = _adapt_query(state)
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "What are my rights?"


def test_adapt_query_no_op_when_messages_present():
    """_adapt_query leaves state unchanged when messages already exist."""
    existing = HumanMessage(content="existing message")
    state: _DatasetInput = {"query": "ignored", "state": "or", "messages": [existing]}  # type: ignore[typeddict-item]
    result = _adapt_query(state)
    assert result == {}


def test_adapt_query_no_op_when_no_query():
    """_adapt_query returns nothing when query is absent."""
    state: _DatasetInput = {"state": "or", "messages": []}  # type: ignore[typeddict-item]
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
    return request


def test_middleware_injects_location_from_state():
    """Middleware appends city/state from agent state to the system prompt."""
    middleware = _SystemPromptFromContext()
    request = _make_middleware_request("Base prompt.", city="Portland", state="OR")

    handler = MagicMock(return_value=MagicMock())
    middleware.wrap_model_call(request, handler)

    assert isinstance(request.system_message, SystemMessage)
    assert "Portland OR" in request.system_message.content
    assert "Base prompt." in request.system_message.content
    handler.assert_called_once_with(request)


def test_middleware_without_city():
    """Middleware works when city is None (state-only location)."""
    middleware = _SystemPromptFromContext()
    request = _make_middleware_request("Base prompt.", city=None, state="OR")

    handler = MagicMock(return_value=MagicMock())
    middleware.wrap_model_call(request, handler)

    assert "OR" in request.system_message.content
    # No leading space before state when city is absent.
    assert "The user is in OR." in request.system_message.content


def test_middleware_uses_custom_prompt_from_context():
    """Middleware uses the prompt from Studio context, not the default."""
    middleware = _SystemPromptFromContext()
    custom = "You are a custom agent."
    request = _make_middleware_request(custom, state="OR")

    handler = MagicMock(return_value=MagicMock())
    middleware.wrap_model_call(request, handler)

    assert custom in request.system_message.content


@pytest.mark.asyncio
async def test_middleware_async_injects_location():
    """Async middleware path also reads city/state from agent state."""
    middleware = _SystemPromptFromContext()
    request = _make_middleware_request("Async base.", city="Eugene", state="OR")

    async def async_handler(req):
        return MagicMock()

    await middleware.awrap_model_call(request, async_handler)

    assert isinstance(request.system_message, SystemMessage)
    assert "Eugene OR" in request.system_message.content
