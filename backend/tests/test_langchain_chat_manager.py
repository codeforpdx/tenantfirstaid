"""Tests for LangChain-based chat manager."""

import pytest

from tenantfirstaid.langchain_chat_manager import (
    LangChainChatManager,
)
from tenantfirstaid.location import OregonCity, UsaState


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
    state = oregon_state
    city = portland_city

    chat_manager = LangChainChatManager()

    """Test that system prompt includes user location."""
    prompt = chat_manager._prepare_system_prompt(city, state)

    assert "Portland OR" in prompt
    assert 'target="_blank"' in prompt  # Citation format.


def test_prepare_system_prompt_includes_city_state(oregon_state, portland_city):
    state = oregon_state
    city = portland_city
    chat_manager = LangChainChatManager()

    instructions = chat_manager._prepare_system_prompt(city, state)
    assert f"The user is in {city.capitalize()} {state.upper()}." in instructions


def test_tools_include_rag_retrieval():
    """Test that tools list includes RAG retrieval tools."""
    chat_manager = LangChainChatManager()

    assert len(chat_manager.tools) == 1
    tool_names = [tool.name for tool in chat_manager.tools]
    assert "retrieve_city_state_laws" in tool_names
