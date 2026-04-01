"""Tests for LangChain-based chat manager."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from tenantfirstaid.langchain_chat_manager import (
    LangChainChatManager,
)
from tenantfirstaid.location import UsaState


def test_system_prompt_includes_city_and_state(oregon_state, portland_city):
    """Test that system prompt includes user location."""
    chat_manager = LangChainChatManager()
    prompt = chat_manager._prepare_system_prompt(portland_city, oregon_state)

    assert "Portland" in prompt
    assert "OR" in prompt


def test_tools_include_rag_retrieval():
    """Test that tools list includes RAG retrieval and letter template tools."""
    chat_manager = LangChainChatManager()

    assert len(chat_manager.tools) == 3
    tool_names = [tool.name for tool in chat_manager.tools]
    assert "retrieve_city_state_laws" in tool_names
    assert "generate_letter" in tool_names
    assert "get_letter_template" in tool_names


def test_system_prompt_no_city(oregon_state):
    """When no city is provided, the location line should mention state only."""
    chat_manager = LangChainChatManager()
    prompt = chat_manager._prepare_system_prompt(None, oregon_state)
    assert "The user is in" in prompt
    assert "OR" in prompt


def test_system_prompt_state_only():
    chat_manager = LangChainChatManager()
    state = UsaState.from_maybe_str("other")
    prompt = chat_manager._prepare_system_prompt(None, state)
    assert "OTHER" in prompt


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


def test_agent_creation_with_thread_id(oregon_state, portland_city):
    cm = LangChainChatManager()
    create = getattr(cm, "_LangChainChatManager__create_agent_for_session")
    agent = create(portland_city, oregon_state, "test-thread")
    assert agent is not None


def test_agent_creation_without_thread_id(oregon_state, portland_city):
    cm = LangChainChatManager()
    create = getattr(cm, "_LangChainChatManager__create_agent_for_session")
    agent = create(portland_city, oregon_state, None)
    assert agent is not None
