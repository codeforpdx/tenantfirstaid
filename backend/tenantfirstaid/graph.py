"""Shared agent components and LangGraph entry point.

Provides the LLM, tools, and graph factory used by both LangChainChatManager
(web app) and `langgraph dev` / LangSmith Cloud deployment.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from langchain.agents import create_agent
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
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


@dataclass
class TFAContext:
    """Runtime context exposed in LangGraph Studio's configuration panel.

    Lawyers can edit the system prompt directly in Studio without redeploying.
    The default value is loaded from system_prompt.md at startup.
    """

    system_prompt: str = field(default=DEFAULT_INSTRUCTIONS)


class _SystemPromptFromContext(AgentMiddleware[Any, TFAContext]):
    """Middleware that reads the system prompt from runtime context.

    This allows the system prompt to be overridden per-run via Studio's
    configuration panel, while still defaulting to system_prompt.md.
    """

    def wrap_model_call(
        self,
        request: ModelRequest[TFAContext],
        handler: Callable[[ModelRequest[TFAContext]], ModelResponse],
    ) -> ModelResponse:
        request.system_message = SystemMessage(
            content=request.runtime.context.system_prompt
        )
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest[TFAContext],
        handler: Callable,
    ) -> ModelResponse:
        request.system_message = SystemMessage(
            content=request.runtime.context.system_prompt
        )
        return await handler(request)


def prepare_system_prompt(city: Optional[OregonCity], state: UsaState) -> SystemMessage:
    """Build the system prompt with location context appended."""
    location = f"{city.title() if city is not None else ''} {state.upper()}"
    return SystemMessage(DEFAULT_INSTRUCTIONS + f"\nThe user is in {location}.\n")


def create_graph(
    system_prompt: Optional[SystemMessage] = None,
    checkpointer: Optional[InMemorySaver] = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Create a Tenant First Aid agent graph.

    Args:
        system_prompt: System prompt to use. When provided (e.g. from the web
            app with location context), the middleware is skipped. When None
            (LangGraph deployment), the middleware reads the prompt from Studio
            context instead.
        checkpointer: Optional checkpointer for multi-turn conversations.

    Returns:
        A compiled LangGraph state graph.
    """
    if system_prompt is not None:
        # Web app path: system prompt has location context baked in.
        return create_agent(
            llm,
            tools,
            system_prompt=system_prompt,
            state_schema=TFAAgentStateSchema,
        )

    # LangGraph deployment path: middleware injects the prompt from
    # Studio's editable configuration panel.
    return create_agent(
        llm,
        tools,
        middleware=[_SystemPromptFromContext()],
        context_schema=TFAContext,
        state_schema=TFAAgentStateSchema,
    )


# Module-level graph instance for langgraph.json to reference.
graph = create_graph(checkpointer=InMemorySaver())
