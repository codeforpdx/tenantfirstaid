"""Tests for LangChain-based chat manager."""

import pytest

from tenantfirstaid.graph import prepare_system_prompt, tools
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
