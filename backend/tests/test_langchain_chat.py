"""Tests for LangChain-based chat manager."""

from typing import Dict
from unittest.mock import Mock, patch

import pytest

from tenantfirstaid.langchain_chat_manager import (
    LangChainChatManager,
    retrieve_city_law,
    retrieve_state_law,
)


@pytest.fixture
def mock_vertex_ai():
    """Mock Vertex AI RAG responses."""
    with patch("tenantfirstaid.langchain_chat.rag.retrieve") as mock_retrieve:
        mock_doc = Mock()
        mock_doc.text = "ORS 90.427 requires 30 days notice..."
        mock_retrieve.return_value.documents = [mock_doc]
        yield mock_retrieve


@pytest.fixture
def chat_manager():
    """Create LangChainChatManager with mocked LLM."""
    with patch("tenantfirstaid.langchain_chat.ChatVertexAI"):
        manager = LangChainChatManager()
        yield manager


def test_retrieve_city_law_filters_correctly(mock_vertex_ai):
    """Test that city law retrieval uses correct filter."""
    d: Dict[str, str] = {
        "query": "eviction notice requirements",
        "city": "portland",
        "state": "or",
    }

    result = retrieve_city_law.invoke(d)

    # Verify filter was constructed correctly.
    call_args = mock_vertex_ai.call_args
    assert 'city: ANY("portland")' in str(call_args)
    assert 'state: ANY("or")' in str(call_args)
    assert "ORS 90.427" in result


def test_retrieve_state_law_filters_correctly(mock_vertex_ai):
    """Test that state law retrieval uses correct filter."""
    d: Dict[str, str] = {"query": "tenant rights", "state": "or"}
    result = retrieve_state_law.invoke(d)

    # Verify filter was constructed correctly.
    call_args = mock_vertex_ai.call_args
    assert 'city: ANY("null")' in str(call_args)
    assert 'state: ANY("or")' in str(call_args)
    assert "ORS 90.427" in result


def test_system_prompt_includes_location(chat_manager):
    """Test that system prompt includes user location."""
    prompt = chat_manager.prepare_system_prompt("Portland", "or")

    assert "Portland OR" in prompt
    assert "888-585-9638" in prompt  # Oregon Law Center phone.
    assert 'target="_blank"' in prompt  # Citation format.


def test_message_format_conversion(chat_manager):
    """Test conversion from session format to LangChain format."""
    from langchain_core.messages import AIMessage, HumanMessage

    session_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "model", "content": "Hi there"},
    ]

    formatted = chat_manager._format_messages(session_messages)

    assert len(formatted) == 2
    assert isinstance(formatted[0], HumanMessage)
    assert isinstance(formatted[1], AIMessage)
    assert formatted[0].content == "Hello"


def test_agent_creation(chat_manager):
    """Test that agent is created with correct configuration."""
    with patch.object(chat_manager, "llm"):
        agent = chat_manager.create_agent_for_session("Portland", "or")

        # Verify agent executor was created.
        assert agent is not None
        assert hasattr(agent, "invoke")


def test_tools_include_rag_retrieval(chat_manager):
    """Test that tools list includes RAG retrieval tools."""
    assert len(chat_manager.tools) == 2
    tool_names = [tool.name for tool in chat_manager.tools]
    assert "retrieve_city_law" in tool_names
    assert "retrieve_state_law" in tool_names
