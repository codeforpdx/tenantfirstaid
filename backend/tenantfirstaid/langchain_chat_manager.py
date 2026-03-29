"""LangChain-based chat manager for tenant legal advice.

This module provides the web application's chat interface, wrapping the shared
agent graph with per-session location context and streaming support.
"""

import logging
import sys
from typing import Any, Dict, Generator, List, Optional, cast

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ContentBlock,
    NonStandardContentBlock,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from .graph import create_graph, prepare_system_prompt
from .location import OregonCity, UsaState


class LangChainChatManager:
    """
    Manages simultaneous chat interactions using LangChain agent architecture.
    """

    logger: logging.Logger
    agent: Optional[CompiledStateGraph] = None

    def __init__(self) -> None:
        """Initialize the LangChain chat manager."""

        # configure logging
        logging.basicConfig(
            level=logging.WARNING,
            stream=sys.stdout,
            format="%(levelname)s: %(message)s (%(filename)s:%(lineno)d)",
        )
        self.logger = logging.getLogger("LangChainChatManager")

        # defer agent instantiation until 'generate_stream_response'
        self.agent = None
        self.system_prompt: Optional[SystemMessage] = None

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

        self.system_prompt = prepare_system_prompt(city, state)

        return create_graph(
            system_prompt=self.system_prompt,
        )

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
        for mode, chunk in self.agent.stream(
            input={
                "messages": messages,
                "city": city,
                "state": state,
            },
            stream_mode=["updates", "custom"],
            config=config,
        ):
            # Custom chunks are emitted directly by tools (e.g. generate_letter).
            if mode == "custom":
                self.logger.debug(chunk)
                yield NonStandardContentBlock(type="non_standard", value=cast(Dict[str, Any], chunk))
                continue

            # outer dict key changes with internal messages (Model, Tool, ...)
            chunk = cast(Dict[str, Any], chunk)
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
                                    self.logger.debug(b)
                                    yield b
                                # reasoning steps (aka "thoughts") from the Model
                                case "reasoning":
                                    if "reasoning" in b:
                                        self.logger.debug(b)
                                        yield b
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
