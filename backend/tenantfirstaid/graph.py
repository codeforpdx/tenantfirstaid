"""Shared agent components and LangGraph entry point.

Provides the LLM, tools, and graph factory used by both LangChainChatManager
(web app) and `langgraph dev` / LangSmith Cloud deployment.
"""

import threading
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any, Callable, List, NotRequired, Optional, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .constants import DEFAULT_INSTRUCTIONS, SINGLETON
from .google_auth import load_gcp_credentials
from .langchain_tools import (
    generate_letter,
    get_active_rag_tools,
    get_letter_template,
)
from .location import OregonCity, TFAAgentStateSchema, UsaState

# Deferred LLM — built on first use so the module can be imported without
# valid GCP credentials (e.g. fork CI that only runs unit tests).
_llm: Optional[ChatGoogleGenerativeAI] = None
"""Lazily-initialized shared LLM instance."""
_llm_lock = threading.Lock()
"""Lock for thread-safe LLM initialization."""


def _get_llm() -> ChatGoogleGenerativeAI:
    """Return the shared LLM instance, creating it on first call.

    Thread-safe lazy initialization of the LLM using configured GCP credentials
    and model parameters.

    Returns:
        ChatGoogleGenerativeAI instance configured with project, model, and safety settings.

    Raises:
        AssertionError: If GOOGLE_APPLICATION_CREDENTIALS is not set.
    """
    global _llm
    with _llm_lock:
        if _llm is None:
            assert SINGLETON.GOOGLE_APPLICATION_CREDENTIALS is not None, (
                "GOOGLE_APPLICATION_CREDENTIALS is not set"
            )
            creds = load_gcp_credentials(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)
            _llm = ChatGoogleGenerativeAI(
                model=SINGLETON.MODEL_NAME,
                max_tokens=SINGLETON.MAX_TOKENS,
                credentials=creds,
                project=SINGLETON.GOOGLE_CLOUD_PROJECT,
                location=SINGLETON.GOOGLE_CLOUD_LOCATION,
                safety_settings=SINGLETON.SAFETY_SETTINGS,
                temperature=SINGLETON.MODEL_TEMPERATURE,
                top_p=SINGLETON.TOP_P,
                seed=0,
                thinking_budget=SINGLETON.THINKING_BUDGET,
                include_thoughts=SINGLETON.SHOW_MODEL_THINKING,
            )
        return _llm


tools: List[BaseTool] = [*get_active_rag_tools(), get_letter_template, generate_letter]
"""Tools available to the agent: active RAG retrievers plus letter generation."""


@dataclass
class TFAContext:
    """Runtime context exposed in LangGraph Studio's configuration panel.

    Lawyers can edit the system prompt directly in Studio without redeploying.
    The default value is loaded from system_prompt.md at startup.
    """

    system_prompt: str = field(default=DEFAULT_INSTRUCTIONS)


class _SystemPromptFromContext(AgentMiddleware[Any, TFAContext]):
    """Middleware that builds the system prompt from context and agent state.

    Reads the base prompt from Studio's configuration panel (exposed as a TFAContext
    field) and appends location context (city/state) from the agent state, mirroring
    what the web app does via prepare_system_prompt(). This allows lawyers to edit
    the system prompt directly in LangSmith Studio without redeploying.
    """

    def _build(self, request: ModelRequest[TFAContext]) -> SystemMessage:
        """Build a system message with location context appended.

        Args:
            request: ModelRequest containing context and agent state.

        Returns:
            SystemMessage with location context from city/state appended.
        """
        ctx = request.runtime.context
        # When the agent runs as a subgraph, LangGraph passes the configurable
        # as a raw dict rather than a deserialized TFAContext instance.
        if isinstance(ctx, TFAContext):
            base = ctx.system_prompt
        else:
            base = ctx.get("system_prompt", DEFAULT_INSTRUCTIONS)  # type: ignore[union-attr]
        state = UsaState.from_maybe_str(request.state.get("state"))
        city = OregonCity.from_maybe_str(request.state.get("city"))
        return _build_system_message(base, city, state)

    def wrap_model_call(
        self,
        request: ModelRequest[TFAContext],
        handler: Callable[[ModelRequest[TFAContext]], ModelResponse],
    ) -> ModelResponse:
        """Wrap synchronous model call with built system message.

        Args:
            request: ModelRequest to be overridden with location-aware system message.
            handler: Callable that handles the model request.

        Returns:
            ModelResponse from the handler.
        """
        return handler(request.override(system_message=self._build(request)))

    async def awrap_model_call(
        self,
        request: ModelRequest[TFAContext],
        handler: Callable[[ModelRequest[TFAContext]], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Wrap asynchronous model call with built system message.

        Args:
            request: ModelRequest to be overridden with location-aware system message.
            handler: Async callable that handles the model request.

        Returns:
            ModelResponse from the handler.
        """
        return await handler(request.override(system_message=self._build(request)))


def _build_system_message(
    base_prompt: str, city: Optional[OregonCity], state: UsaState
) -> SystemMessage:
    """Build a SystemMessage with location context appended.

    Appends a line indicating the user's city (if specified) and state to the base
    prompt, helping the agent tailor responses to local laws and jurisdictions.

    Args:
        base_prompt: Base system prompt text.
        city: User's [city](`~location.OregonCity`), or None for state-level queries.
        state: User's [state](`~location.UsaState`).

    Returns:
        SystemMessage with location context appended.
    """
    parts = ([city.title()] if city is not None else []) + [state.upper()]
    location = " ".join(parts)
    return SystemMessage(base_prompt + f"\nThe user is in {location}.\n")


def prepare_system_prompt(city: Optional[OregonCity], state: UsaState) -> SystemMessage:
    """Build the default system prompt with location context appended.

    Args:
        city: User's [city](`~location.OregonCity`), or None for state-level queries.
        state: User's [state](`~location.UsaState`).

    Returns:
        SystemMessage with default instructions and location context.
    """
    return _build_system_message(DEFAULT_INSTRUCTIONS, city, state)


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
    model = _get_llm()

    if system_prompt is not None:
        # Web app path: system prompt has location context baked in.
        return create_agent(
            model,
            tools,
            system_prompt=system_prompt,
            state_schema=TFAAgentStateSchema,
            checkpointer=checkpointer,
        )

    # LangGraph deployment path: middleware injects the prompt from
    # Studio's editable configuration panel. context_schema is NOT set here
    # because this graph runs as a subgraph inside graph() — the outer graph
    # owns the context and propagates it. Declaring it on both levels causes
    # LangSmith to patch execution_info during __start__ before a run context
    # exists.
    return create_agent(
        model,
        tools,
        middleware=[_SystemPromptFromContext()],
        state_schema=TFAAgentStateSchema,
        checkpointer=checkpointer,
    )


class _DeploymentInput(TypedDict):
    """Input schema for the LangGraph deployment wrapper graph.

    Defines the fields accepted by LangSmith Studio's input panel. The ``_adapt_query``
    node converts the query to a HumanMessage before the agent runs.
    """

    query: str
    """User's question."""
    state: UsaState
    """User's state."""
    city: NotRequired[Optional[OregonCity]]
    """User's city, optional."""


class _DatasetInput(TFAAgentStateSchema):
    """Internal state schema for the deployment wrapper graph.

    Extends TFAAgentStateSchema with an optional query field so the adapt node
    can read it and convert it to a HumanMessage. This schema is used internally
    by the wrapper and should not be exposed in user-facing APIs.
    """

    query: NotRequired[Optional[str]]
    """User query string."""


def _adapt_query(state: _DatasetInput) -> dict:
    """Convert a bare query string to a HumanMessage if messages is empty.

    Enables the graph to accept both dataset-style inputs (query/city/state) for
    LangSmith evaluation and standard messages-based interfaces. If a query is
    provided but messages is empty, it is converted to a HumanMessage and returned
    in the state update.

    Args:
        state: Current graph state.

    Returns:
        State dict with messages field set if query was present and messages was empty.
    """
    if state.get("query") and not state.get("messages"):
        return {"messages": [HumanMessage(content=state["query"])]}
    return {}


def graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Graph factory for LangGraph deployment via langgraph.json.

    Builds a wrapper graph that adapts dataset-style inputs (query/city/state) to
    the agent's messages-based interface. The wrapper runs the inner ``create_graph``
    agent as a subgraph and exposes Studio context for editable system prompts.

    Called by LangGraph's loader at deployment time; defers credential loading so
    the module remains importable without valid GCP credentials (useful for CI).

    Returns:
        A compiled LangGraph state graph for deployment.
    """
    inner = create_graph()  # no checkpointer — outer graph owns the checkpoint
    # fmt: off
    builder: StateGraph = StateGraph(_DatasetInput, input_schema=_DeploymentInput, context_schema=TFAContext)  # type: ignore
    # fmt: on
    builder.add_node("adapt", _adapt_query)
    builder.add_node("agent", inner)
    builder.add_edge(START, "adapt")
    builder.add_edge("adapt", "agent")
    return builder.compile(checkpointer=InMemorySaver())
