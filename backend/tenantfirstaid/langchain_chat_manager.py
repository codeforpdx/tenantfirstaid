"""LangChain-based chat manager for tenant legal advice.

This module provides a LangChain implementation that replaces the direct
Google Gemini API calls with a standardized agent-based architecture.
"""

from pathlib import Path

# from enum import Enum, StrEnum
from pprint import pprint
from typing import List, Optional

from langchain.agents import AgentState, create_agent
from langchain.tools import ToolRuntime

# from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage

# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool, tool

# from langchain_google_vertexai.vectorstores.vectorstores import (
#     VectorSearchVectorStoreDatastore,
# )
from langchain_google_community import VertexAISearchRetriever
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from .constants import DEFAULT_INSTRUCTIONS, SINGLETON


def city_or_state_input_sanitizer(location: Optional[str], max_len: int = 9) -> str:
    """Validate and sanitize city or state input."""
    if location is None or not isinstance(location, str):
        return ""
    if not location.isalpha():
        raise ValueError(f"Invalid city or state input: {location}")
    if len(location) < 2 or len(location) > max_len:
        raise ValueError(f"Invalid city or state input length: {location}")
    return location.lower()


# class _InnerOregonCity(StrEnum):
#     PORTLAND = "portland"
#     EUGENE = "eugene"


# class OregonCity(BaseModel, arbitrary_types_allowed=True):
#     value: Optional[_InnerOregonCity] = None

#     @classmethod
#     def from_str(cls, v: Optional[str]) -> "OregonCity":
#         instance = cls()
#         if v is None:
#             instance.value = None
#         else:
#             try:
#                 instance.value = _InnerOregonCity(v.lower())
#             except ValueError:
#                 instance.value = None
#         return instance

#     # def __init__(self, v: str):
#     #     try:
#     #         if v is None:
#     #             self.value = None
#     #         else:
#     #             self.value = _InnerOregonCity(v.lower())
#     #     except ValueError:
#     #         self.value = None
#     #     except Exception as e:
#     #         raise e
#     #     super().__init__()

#     def __repr__(self) -> str:
#         return str(self.value) if self.value is not None else "null"

#     def else_empty(self) -> str:
#         return str(self.value) if self.value is not None else ""

#     def lower(self) -> str:
#         return self.else_empty().lower()

#     def upper(self) -> str:
#         return self.else_empty().upper()


# class _InnerUsaState(StrEnum):
#     OREGON = "or"
#     OTHER = "OTHER"

# class UsaState(BaseModel, arbitrary_types_allowed=True):
#     value: Optional[_InnerUsaState] = None

#     # def __init__(self, v: str):
#     #     try:
#     #         if v is None:
#     #             self.value = None
#     #         else:
#     #             self.value = _InnerUsaState(v.lower())
#     #     except ValueError:
#     #         self.value = None
#     #     except Exception as e:
#     #         raise e
#     #     super().__init__()

#     @classmethod
#     def from_str(cls, v: Optional[str]) -> "UsaState":
#         instance = cls()
#         if v is None:
#             instance.value = None
#         else:
#             try:
#                 instance.value = _InnerUsaState(v.lower())
#             except ValueError:
#                 instance.value = None
#         return instance

#     def __repr__(self) -> str:
#         return str(self.value) if self.value is not None else "null"

#     def else_empty(self) -> str:
#         return str(self.value) if self.value is not None else ""

#     def lower(self) -> str:
#         return self.else_empty().lower()

#     def upper(self) -> str:
#         return self.else_empty().upper()


class TFAAgentStateSchema(AgentState):
    state: str
    city: Optional[str]


# vector_store = VectorSearchVectorStoreDatastore.from_components(
#     project_id=GOOGLE_CLOUD_PROJECT,
#     region=GOOGLE_CLOUD_LOCATION,
#     index_id=VERTEX_AI_DATASTORE,
#     endpoint_id="fix-me-later",
# )


class StateLawInputSchema(BaseModel, arbitrary_types_allowed=True):
    query: str
    state: str
    runtime: ToolRuntime


@tool(args_schema=StateLawInputSchema)
def retrieve_state_law(query: str, state: str, runtime: ToolRuntime) -> str:
    """Retrieve state-wide housing laws from the RAG corpus.

    Use this tool for general state law questions or when city is not specified.

    Args:
        query: The user's legal question
        state: The user's state (e.g., "or")
        runtime: Tool runtime context

    Returns:
        Relevant legal passages from state laws
    """

    safe_state: str = city_or_state_input_sanitizer(state, max_len=2).lower()

    pprint(runtime.context)

    # rag = vector_store.as_retriever(
    #     search_kwargs={"k": 5},
    #     filter=f'city: ANY("null") AND state: ANY("{state.lower()}")',
    # )

    rag = VertexAISearchRetriever(
        name=str(Path(SINGLETON.VERTEX_AI_DATASTORE).parts[-1]),  # type: ignore [unresolved-attribute]
        project_id=SINGLETON.GOOGLE_CLOUD_PROJECT,  # type: ignore [unresolved-attribute]
        location_id=SINGLETON.GOOGLE_CLOUD_LOCATION,  # type: ignore [unresolved-attribute]
        data_store_id=SINGLETON.VERTEX_AI_DATASTORE,  # type: ignore [unresolved-attribute]
        # max_results=5,
        filter=f'city: ANY("null") AND state: ANY("{safe_state}")',
    )

    docs = rag.invoke(
        input=query,
        # filter=f'city: ANY("null") AND state: ANY("{state.lower()}")'
    )

    return "\n\n".join([doc.page_content for doc in docs])


class CityLawInputSchema(BaseModel, arbitrary_types_allowed=True):
    query: str
    city: str
    state: str


@tool(args_schema=CityLawInputSchema)
def retrieve_city_law(query: str, city: str, state: str) -> str:
    """Retrieve city-specific housing laws from the RAG corpus.

    Use this tool when the user has specified their city location.

    Args:
        query: The user's legal question
        city: The user's city (e.g., "portland", "eugene")
        state: The user's state (e.g., "or")

    Returns:
        Relevant legal passages from city-specific laws
    """

    safe_city: str = city_or_state_input_sanitizer(city).lower()
    safe_state: str = city_or_state_input_sanitizer(state, max_len=2).lower()

    # rag = vector_store.as_retriever(
    #     search_kwargs={"k": 5},
    #     filter=f'city: ANY("{city.lower()}") AND state: ANY("{state.lower()}")',
    # )

    rag = VertexAISearchRetriever(
        name=str(Path(SINGLETON.VERTEX_AI_DATASTORE).parts[-1]),  # type: ignore [unresolved-attribute]
        project_id=SINGLETON.GOOGLE_CLOUD_PROJECT,  # type: ignore [unresolved-attribute]
        location_id=SINGLETON.GOOGLE_CLOUD_LOCATION,  # type: ignore [unresolved-attribute]
        data_store_id=SINGLETON.VERTEX_AI_DATASTORE,  # type: ignore [unresolved-attribute]
        # max_results=5,
        filter=f'city: ANY("{safe_city}") AND state: ANY("{safe_state}")',
    )

    docs = rag.invoke(
        input=query,
    )

    return "\n\n".join([doc.page_content for doc in docs])


class LangChainChatManager:
    """Manages chat interactions using LangChain agent architecture."""

    def __init__(self) -> None:
        """Initialize the LangChain chat manager with Vertex AI integration."""

        # Initialize ChatVertexAI with same config as current implementation.
        self.llm = ChatGoogleGenerativeAI(
            model=SINGLETON.MODEL_NAME,  # type: ignore [unresolved-attribute]
            temperature=SINGLETON.MODEL_TEMPERATURE,  # type: ignore [unresolved-attribute]
            max_tokens=SINGLETON.MAX_TOKENS,  # type: ignore [unresolved-attribute]
            project=SINGLETON.GOOGLE_CLOUD_PROJECT,  # type: ignore [unresolved-attribute]
            location=SINGLETON.GOOGLE_CLOUD_LOCATION,  # type: ignore [unresolved-attribute]
            safety_settings=SINGLETON.SAFETY_SETTINGS,  # type: ignore [unresolved-attribute]
            # Thinking config for Gemini 2.5 Pro.
            # enable_thinking=os.getenv("SHOW_MODEL_THINKING", "false").lower() == "true",
        )

        # self.rag = VertexAISearchRetriever(
        #     name=str(Path(self.SINGLETON.VERTEX_AI_DATASTORE).parts[-1]),
        #     project_id=self.SINGLETON.GOOGLE_CLOUD_PROJECT,
        #     location_id=self.SINGLETON.GOOGLE_CLOUD_LOCATION,
        #     data_store_id=self.SINGLETON.VERTEX_AI_DATASTORE,
        #     # max_results=5,
        # )

        # Create tools for RAG retrieval.
        # self.tools: List[BaseTool] = [retrieve_city_law, retrieve_state_law]
        self.tools: List[BaseTool] = []  # FIXME!

    def create_agent_for_session(self, city: str, state: str) -> CompiledStateGraph:
        """Create an agent instance configured for the user's location.

        Args:
            city: User's city (e.g., "portland", "null")
            state: User's state (e.g., "or")

        Returns:
            AgentExecutor configured with tools and system prompt
        """

        safe_city: str = city_or_state_input_sanitizer(city).lower()
        safe_state: str = city_or_state_input_sanitizer(state, max_len=2).lower()
        system_prompt = SystemMessage(self.prepare_system_prompt(safe_city, safe_state))

        # # Create prompt template with system message and conversation history.
        # prompt = ChatPromptTemplate.from_messages(
        #     [
        #         ("system", system_prompt.text()),
        #         MessagesPlaceholder(variable_name="chat_history", optional=True),
        #         ("human", "{input}"),
        #         MessagesPlaceholder(variable_name="agent_scratchpad"),
        #     ]
        # )

        # Create agent with tools.
        return create_agent(
            self.llm,
            self.tools,
            system_prompt=system_prompt,
            state_schema=TFAAgentStateSchema,
            # checkpointer=InMemorySaver(),
        )

    def prepare_system_prompt(self, city: str, state: str) -> str:
        """Prepare detailed system instructions for the agent.

        This matches the current DEFAULT_INSTRUCTIONS with location context.

        Args:
            city: User's city
            state: User's state

        Returns:
            System prompt string with instructions and location context
        """

        safe_city: str = city_or_state_input_sanitizer(city).lower()
        safe_state: str = city_or_state_input_sanitizer(state, max_len=2).upper()

        VALID_CITIES = {"Portland", "Eugene", "null", None}
        VALID_STATES = {"OR"}

        # Validate and sanitize inputs
        city_clean = safe_city.title() if safe_city else "null"
        state_upper = safe_state.upper() if safe_state else "OR"

        if city_clean not in VALID_CITIES:
            city_clean = "null"
        if state_upper not in VALID_STATES:
            raise ValueError(f"Invalid state: {state}")

        # Add city and state filters if they are set
        instructions = DEFAULT_INSTRUCTIONS
        instructions += f"\nThe user is in {city_clean if city_clean != 'null' else ''} {state_upper}.\n"
        return instructions

    def generate_streaming_response(
        self, messages: list[AnyMessage], city: str, state: str
    ):
        """Generate streaming response using LangChain agent.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            city: User's city
            state: User's state

        Yields:
            Response chunks as they are generated
        """

        safe_city: str = city_or_state_input_sanitizer(city).lower()
        safe_state: str = city_or_state_input_sanitizer(state, max_len=2).lower()

        agent = self.create_agent_for_session(safe_city, safe_state)

        # Split messages into conversation history and current query.
        (conversation_history, current_query) = (messages[:-1], [messages[-1]])

        # Stream the agent response.
        for chunk in agent.stream(
            {
                "messages": current_query,
                "context": conversation_history,
                "city": city,
                "state": state,
            },
            stream_mode="updates",
        ):
            # Extract messages from chunk.
            if "messages" in chunk:
                messages = chunk["messages"]
                if messages and isinstance(messages[-1], AIMessage):
                    yield messages[-1].content

    # def _format_messages(
    #     self, messages: list[AnyMessage]
    # ) -> list[HumanMessage | AIMessage]:
    #     """Convert session messages to LangChain message format.

    #     Args:
    #         messages: List of message dictionaries with 'role' and 'content' keys

    #     Returns:
    #         List of LangChain message objects
    #     """
    #     formatted = []
    #     for msg in messages:
    #         if msg["role"] == "user":
    #             formatted.append(HumanMessage(content=msg.content))
    #         else:  # assistant/model
    #             formatted.append(AIMessage(content=msg.content))
    #     return formatted
