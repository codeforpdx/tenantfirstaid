"""LangChain-based chat manager for tenant legal advice.

This module provides a LangChain implementation that replaces the direct
Google Gemini API calls with a standardized agent-based architecture.
"""

import os
from typing import Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
from vertexai.preview import rag

from tenantfirstaid.chat import DEFAULT_INSTRUCTIONS

MODEL = os.getenv("MODEL_NAME", "gemini-2.5-pro")
VERTEX_AI_DATASTORE = os.getenv("VERTEX_AI_DATASTORE")


@tool
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
    retrieval_query = rag.RagQuery(
        text=query,
        filter=f'city: ANY("{city.lower()}") AND state: ANY("{state.lower()}")',
    )

    response = rag.retrieve(
        datastore=VERTEX_AI_DATASTORE,
        query=retrieval_query,
        max_results=5,
    )

    return "\n\n".join([doc.text for doc in response.documents])


@tool
def retrieve_state_law(query: str, state: str) -> str:
    """Retrieve state-wide housing laws from the RAG corpus.

    Use this tool for general state law questions or when city is not specified.

    Args:
        query: The user's legal question
        state: The user's state (e.g., "or")

    Returns:
        Relevant legal passages from state laws
    """
    retrieval_query = rag.RagQuery(
        text=query,
        filter=f'city: ANY("null") AND state: ANY("{state.lower()}")',
    )

    response = rag.retrieve(
        datastore=VERTEX_AI_DATASTORE,
        query=retrieval_query,
        max_results=5,
    )

    return "\n\n".join([doc.text for doc in response.documents])


class LangChainChatManager:
    """Manages chat interactions using LangChain agent architecture."""

    def __init__(self) -> None:
        """Initialize the LangChain chat manager with Vertex AI integration."""
        # Initialize ChatVertexAI with same config as current implementation.
        self.llm = ChatVertexAI(
            model_name=MODEL,
            temperature=0,
            max_tokens=65535,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            # Safety settings to match current implementation.
            safety_settings={
                "HARM_CATEGORY_HATE_SPEECH": "OFF",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "OFF",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "OFF",
                "HARM_CATEGORY_HARASSMENT": "OFF",
            },
            # Thinking config for Gemini 2.5 Pro.
            enable_thinking=os.getenv("SHOW_MODEL_THINKING", "false").lower()
            == "true",
        )

        # Create tools for RAG retrieval.
        self.tools = [retrieve_city_law, retrieve_state_law]

    def create_agent_for_session(self, city: str, state: str) -> AgentExecutor:
        """Create an agent instance configured for the user's location.

        Args:
            city: User's city (e.g., "portland", "null")
            state: User's state (e.g., "or")

        Returns:
            AgentExecutor configured with tools and system prompt
        """
        system_prompt = self.prepare_system_prompt(city, state)

        # Create prompt template with system message and conversation history.
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Create agent with tools.
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        # Create agent executor.
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
        )

        return agent_executor

    def prepare_system_prompt(self, city: str, state: str) -> str:
        """Prepare detailed system instructions for the agent.

        This matches the current DEFAULT_INSTRUCTIONS with location context.

        Args:
            city: User's city
            state: User's state

        Returns:
            System prompt string with instructions and location context
        """
        instructions = DEFAULT_INSTRUCTIONS
        instructions += (
            f"\nThe user is in {city if city != 'null' else ''} {state.upper()}.\n"
        )
        return instructions

    def generate_streaming_response(
        self, messages: list[dict[str, Any]], city: str, state: str
    ):
        """Generate streaming response using LangChain agent.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            city: User's city
            state: User's state

        Yields:
            Response chunks as they are generated
        """
        agent = self.create_agent_for_session(city, state)

        # Convert messages to LangChain format.
        conversation_history = self._format_messages(messages[:-1])
        current_query = messages[-1]["content"]

        # Stream the agent response.
        for chunk in agent.stream(
            {
                "input": current_query,
                "chat_history": conversation_history,
                "city": city,
                "state": state,
            }
        ):
            # Extract output from chunk.
            if "output" in chunk:
                yield chunk["output"]

    def _format_messages(
        self, messages: list[dict[str, Any]]
    ) -> list[HumanMessage | AIMessage]:
        """Convert session messages to LangChain message format.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            List of LangChain message objects
        """
        formatted = []
        for msg in messages:
            if msg["role"] == "user":
                formatted.append(HumanMessage(content=msg["content"]))
            else:  # assistant/model
                formatted.append(AIMessage(content=msg["content"]))
        return formatted
