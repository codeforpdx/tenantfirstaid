"""Shared agent components and LangGraph entry point.

Provides the LLM, tools, and graph factory used by both LangChainChatManager
(web app) and `langgraph dev` / LangSmith Cloud deployment.
"""

from typing import List, Optional

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from .constants import DEFAULT_INSTRUCTIONS, SINGLETON
from .langchain_tools import (
    generate_letter,
    get_letter_template,
    retrieve_city_state_laws,
)
from .location import OregonCity, TFAAgentStateSchema, UsaState

# Shared LLM instance.
llm = ChatGoogleGenerativeAI(
    model=SINGLETON.MODEL_NAME,
    max_tokens=SINGLETON.MAX_TOKENS,
    project=SINGLETON.GOOGLE_CLOUD_PROJECT,
    location=SINGLETON.GOOGLE_CLOUD_LOCATION,
    safety_settings=SINGLETON.SAFETY_SETTINGS,
    temperature=SINGLETON.MODEL_TEMPERATURE,
    seed=0,
    thinking_budget=-1,
    include_thoughts=SINGLETON.SHOW_MODEL_THINKING,
)

# Shared tool list.
tools: List[BaseTool] = [retrieve_city_state_laws, get_letter_template, generate_letter]


def prepare_system_prompt(city: Optional[OregonCity], state: UsaState) -> SystemMessage:
    """Build the system prompt with location context appended."""
    location = f"{city.title() if city is not None else ''} {state.upper()}"
    return SystemMessage(DEFAULT_INSTRUCTIONS + f"\nThe user is in {location}.\n")


def create_graph(
    system_prompt: Optional[SystemMessage] = None,
    checkpointer: Optional[InMemorySaver] = None,
) -> CompiledStateGraph:
    """Create a Tenant First Aid agent graph.

    Args:
        system_prompt: System prompt to use. Defaults to DEFAULT_INSTRUCTIONS
            without location context (suitable for LangGraph deployment where
            location flows through the agent state).
        checkpointer: Optional checkpointer for multi-turn conversations.

    Returns:
        A compiled LangGraph state graph.
    """
    return create_agent(
        llm,
        tools,
        system_prompt=system_prompt or DEFAULT_INSTRUCTIONS,
        state_schema=TFAAgentStateSchema,
        checkpointer=checkpointer,
    )


# Module-level graph instance for langgraph.json to reference.
graph = create_graph(checkpointer=InMemorySaver())
