"""LangChain-based chat manager for tenant legal advice.

This module provides a LangChain implementation that replaces the direct
Google Gemini API calls with a standardized agent-based architecture.
"""

from pathlib import Path
from typing import List, Optional

from langchain.agents import create_agent

# from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.state import CompiledStateGraph

from .constants import DEFAULT_INSTRUCTIONS, SINGLETON
from .langchain_tools import retrieve_city_law, retrieve_state_law
from .location import TFAAgentStateSchema, city_or_state_input_sanitizer


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
            input={
                "messages": current_query,
                "context": conversation_history,
                "city": city,
                "state": state,
            },
            stream_mode="updates",
        ):
            # outer dict key changes with internal messages (Model, Tool, ...)
            chunk_k = list(chunk.keys())[0]

            # Specialize handling/printing based on each message class/type
            for m in chunk[chunk_k]["messages"]:
                match m:
                    # Send message content to chat client
                    case AIMessage():
                        yield m.content

                    case ToolMessage():
                        print(f"      {m}")
                    # Fall-through case
                    case _:
                        print(f"{type(m)}: {m}")
