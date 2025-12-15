"""LangChain-based chat manager for tenant legal advice.

This module provides a LangChain implementation that replaces the direct
Google Gemini API calls with a standardized agent-based architecture.
"""

import logging
import sys
from typing import Generator, List, Optional

from langchain.agents import create_agent

# from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.state import CompiledStateGraph

from .constants import DEFAULT_INSTRUCTIONS, SINGLETON
from .langchain_tools import retrieve_city_state_laws
from .location import OregonCity, TFAAgentStateSchema, UsaState


def starting_message_helper(content: str) -> HumanMessage:
    return HumanMessage(content=content)


class LangChainChatManager:
    """Manages chat interactions using LangChain agent architecture."""

    logger: logging.Logger

    def __init__(self) -> None:
        """Initialize the LangChain chat manager with Vertex AI integration."""

        # configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stdout,
            format="%(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        )
        self.logger = logging.getLogger("LangChainChatManager")

        # Initialize ChatVertexAI with same config as current implementation.
        self.llm = ChatGoogleGenerativeAI(
            model=SINGLETON.MODEL_NAME,
            temperature=SINGLETON.MODEL_TEMPERATURE,
            max_tokens=SINGLETON.MAX_TOKENS,
            project=SINGLETON.GOOGLE_CLOUD_PROJECT,
            location=SINGLETON.GOOGLE_CLOUD_LOCATION,
            safety_settings=SINGLETON.SAFETY_SETTINGS,
            # Thinking config for Gemini 2.5 Pro.
            # enable_thinking=os.getenv("SHOW_MODEL_THINKING", "false").lower() == "true",
        )

        # Specify tools for RAG retrieval.
        self.tools: List[BaseTool] = [retrieve_city_state_laws]

    def __create_agent_for_session(
        self, city: Optional[OregonCity], state: UsaState
    ) -> CompiledStateGraph:
        """Create an agent instance configured for the user's location.

        Args:
            city: User's city (e.g., "portland", None)
            state: User's state (e.g., "or")

        Returns:
            AgentExecutor configured with tools and system prompt
        """

        system_prompt = SystemMessage(self.__prepare_system_prompt(city, state))

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

    def __prepare_system_prompt(
        self, city: Optional[OregonCity], state: UsaState
    ) -> str:
        """Prepare detailed system instructions for the agent.

        This matches the current DEFAULT_INSTRUCTIONS with location context.

        Args:
            city: User's city
            state: User's state

        Returns:
            System prompt string with instructions and location context
        """

        # Add city and state filters if they are set
        instructions = DEFAULT_INSTRUCTIONS
        instructions += f"\nThe user is in {city.title() if city is not None else ''} {state.upper()}.\n"
        return instructions

    # TODO
    def generate_response(
        self, messages: list[AnyMessage], city: Optional[OregonCity], state: UsaState
    ):
        raise NotImplementedError

    def generate_streaming_response(
        self, messages: list[AnyMessage], city: Optional[OregonCity], state: UsaState
    ) -> Generator:
        """Generate streaming response using LangChain agent.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            city: User's city
            state: User's state

        Yields:
            Response chunks as they are generated
        """

        agent = self.__create_agent_for_session(city, state)

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

            # TODO: refactor this match/yield into a function
            # Specialize handling/printing based on each message class/type
            for m in chunk[chunk_k]["messages"]:
                match m:
                    # Messages sent by the Model
                    case AIMessage():
                        for b in m.content_blocks:
                            match b["type"]:
                                # text responses from the Model
                                case "text":
                                    yield b["text"]
                                case "reasoning":
                                    if "reasoning" in b:
                                        yield b["reasoning"]
                                # the Model calling a tool
                                case "tool_call":
                                    self.logger.info(b)
                                case "server_tool_call":
                                    self.logger.info(b)

                    # Messages sent back by a tool
                    case ToolMessage():
                        for b in m.content_blocks:
                            match b["type"]:
                                case "text":
                                    self.logger.info(b["text"])
                                case "invalid_tool_call":
                                    self.logger.error(b)
                                case _:
                                    self.logger.debug(f"ToolMessage: {m}")

                    # Fall-through case
                    case _:
                        self.logger.debug(f"{type(m)}: {m}")
