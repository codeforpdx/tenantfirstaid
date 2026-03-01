"""LangChain-based chat manager for tenant legal advice.

This module provides a LangChain implementation that replaces the direct
Google Gemini API calls with a standardized agent-based architecture.
"""

import logging
import sys
from typing import Any, Dict, Generator, List, Optional

from langchain.agents import create_agent

# from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ContentBlock,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
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


def starting_message_helper(content: str) -> HumanMessage:
    return HumanMessage(content=content)


class LangChainChatManager:
    """
    Manages simultaneous chat interactions using LangChain agent architecture.
    """

    logger: logging.Logger
    llm: ChatGoogleGenerativeAI
    tools: List[BaseTool]
    agent: Optional[CompiledStateGraph] = None

    def __init__(self) -> None:
        """Initialize the LangChain chat manager with Vertex AI integration."""

        # configure logging
        logging.basicConfig(
            level=logging.WARNING,
            stream=sys.stdout,
            format="%(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        )
        self.logger = logging.getLogger("LangChainChatManager")

        # Initialize ChatVertexAI with same config as current implementation.
        self.llm = ChatGoogleGenerativeAI(
            model=SINGLETON.MODEL_NAME,  # main chat model
            max_tokens=SINGLETON.MAX_TOKENS,  # budget
            project=SINGLETON.GOOGLE_CLOUD_PROJECT,
            location=SINGLETON.GOOGLE_CLOUD_LOCATION,
            safety_settings=SINGLETON.SAFETY_SETTINGS,
            # consistency
            temperature=SINGLETON.MODEL_TEMPERATURE,  # 1.0 is default for Gemini 3+, https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai#instantiation
            seed=0,
            # reasoning
            thinking_budget=-1,  # gemini 2.5 specific (use thinking_level for 3+ https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai#thinking-support)
            include_thoughts=SINGLETON.SHOW_MODEL_THINKING,
        )

        # Specify tools for RAG retrieval.
        self.tools = [retrieve_city_state_laws, get_letter_template, generate_letter]

        # defer agent instantiation until 'generate_stream_response'
        self.agent = None

    def __create_agent_for_session(
        self, city: Optional[OregonCity], state: UsaState, thread_id: Optional[str]
    ) -> CompiledStateGraph:
        """Create an agent instance configured for the user's location.

        Args:
            city: User's city (e.g., "portland", None)
            state: User's state (e.g., "or")

        Returns:
            AgentExecutor configured with tools and system prompt
        """

        self.system_prompt = SystemMessage(self._prepare_system_prompt(city, state))

        if thread_id is None:
            checkpointer_or_none = None
        else:
            checkpointer_or_none = InMemorySaver()

        # Create agent with tools.
        return create_agent(
            self.llm,
            self.tools,
            system_prompt=self.system_prompt,
            state_schema=TFAAgentStateSchema,
            checkpointer=checkpointer_or_none,
        )

    def _prepare_system_prompt(
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
        self,
        messages: list[AnyMessage],
        city: Optional[OregonCity],
        state: UsaState,
        thread_id: Optional[str],
    ):
        if self.agent is None:
            self.agent = self.__create_agent_for_session(city, state, thread_id)

        raise NotImplementedError

    def generate_streaming_response(
        self,
        messages: List[AnyMessage | Dict[str, Any]],
        city: Optional[OregonCity],
        state: UsaState,
        thread_id: Optional[str],
    ) -> Generator[ContentBlock, Any, None]:
        """Generate streaming response using LangChain agent.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
                      where role is one of 'human', 'user', 'ai', 'assistant',
                      'function', 'tool', 'system', or 'developer'.
            city: User's city
            state: User's state

        Yields:
            Response chunks as they are generated
        """

        if self.agent is None:
            self.agent = self.__create_agent_for_session(city, state, thread_id)

        if thread_id is not None:
            config: RunnableConfig = RunnableConfig(
                configurable={"thread_id": thread_id}
            )
        else:
            config = RunnableConfig()

        # Stream the agent response.
        for chunk in self.agent.stream(
            input={
                "messages": messages,
                "city": city,
                "state": state,
            },
            stream_mode="updates",
            config=config,
        ):
            # outer dict key changes with internal messages (Model, Tool, ...)
            if not chunk:
                continue
            chunk_k = next(iter(chunk))

            # TODO: refactor this match/yield into a function
            # Specialize handling/printing based on each message class/type
            for m in chunk[chunk_k]["messages"]:
                # Extend caller's list so tool messages are included in the agent's running context.
                messages.append(m)

                match m:
                    # Messages sent by the Model
                    case AIMessage():
                        for b in m.content_blocks:
                            match b["type"]:
                                # text responses from the Model
                                case "text":
                                    yield b
                                # reasoning steps (aka "thoughts") from the Model
                                case "reasoning":
                                    if "reasoning" in b:
                                        yield b
                                # the Model calling a tool
                                case "tool_call":
                                    if b["name"] == "generate_letter":
                                        letter = b["args"].get("letter")
                                        if letter:
                                            self.logger.info(b)
                                            yield {"type": "letter", "letter": letter}
                                        else:
                                            self.logger.warning(
                                                "generate_letter called with missing or empty letter arg."
                                            )
                                    else:
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
