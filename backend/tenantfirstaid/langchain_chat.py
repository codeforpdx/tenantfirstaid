"""LangChain-based chat manager for tenant legal advice.

This module provides a LangChain implementation that replaces the direct
Google Gemini API calls with a standardized agent-based architecture.
"""

import os
from typing import Any, Optional
from pathlib import Path

from langchain.agents import create_agent, AgentState
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
# from langchain_google_vertexai.vectorstores.vectorstores import (
#     VectorSearchVectorStoreDatastore,
# )
from langchain_google_community import VertexAISearchRetriever

from langchain_google_vertexai import HarmBlockThreshold, HarmCategory


from tenantfirstaid.chat import DEFAULT_INSTRUCTIONS

if Path("../.env").exists():
    from dotenv import load_dotenv
    load_dotenv(override=True)

MODEL = os.getenv("MODEL_NAME", "gemini-2.5-pro")

if (GOOGLE_CLOUD_PROJECT := os.getenv("GOOGLE_CLOUD_PROJECT")) is None:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")

if (GOOGLE_CLOUD_LOCATION := os.getenv("GOOGLE_CLOUD_LOCATION")) is None:
    raise ValueError("GOOGLE_CLOUD_LOCATION environment variable is not set.")

if (VERTEX_AI_DATASTORE := os.getenv("VERTEX_AI_DATASTORE")) is None:
    raise ValueError("VERTEX_AI_DATASTORE environment variable is not set.")

class TFAAgentState(AgentState):
    state: Optional[str]
    city: Optional[str]

# vector_store = VectorSearchVectorStoreDatastore.from_components(
#     project_id=GOOGLE_CLOUD_PROJECT,
#     region=GOOGLE_CLOUD_LOCATION,
#     index_id=VERTEX_AI_DATASTORE,
#     endpoint_id="fix-me-later",
# )



@tool(parse_docstring=True)
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

    # rag = vector_store.as_retriever(
    #     search_kwargs={"k": 5},
    #     filter=f'city: ANY("{city.lower()}") AND state: ANY("{state.lower()}")',
    # )

    if VERTEX_AI_DATASTORE is None:
        raise ValueError("VERTEX_AI_DATASTORE environment variable is not set.")

    rag = VertexAISearchRetriever(
        name=str(Path(VERTEX_AI_DATASTORE).parts[-2:-1]),
        project_id=GOOGLE_CLOUD_PROJECT,
        location_id=GOOGLE_CLOUD_LOCATION,
        data_store_id=VERTEX_AI_DATASTORE,
        max_results=5,
        filter=f'city: ANY("{city.lower()}") AND state: ANY("{state.lower()}")',
    )

    docs = rag.invoke(
        input=query,
    )

    return "\n\n".join([doc.page_content for doc in docs])


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

    # rag = vector_store.as_retriever(
    #     search_kwargs={"k": 5},
    #     filter=f'city: ANY("null") AND state: ANY("{state.lower()}")',
    # )

    if VERTEX_AI_DATASTORE is None:
        raise ValueError("VERTEX_AI_DATASTORE environment variable is not set.")

    rag = VertexAISearchRetriever(
        name=str(Path(VERTEX_AI_DATASTORE).parts[-2:-1]),
        project_id=GOOGLE_CLOUD_PROJECT,
        location_id=GOOGLE_CLOUD_LOCATION,
        data_store_id=VERTEX_AI_DATASTORE,
        max_results=5,
        filter=f'city: ANY("null") AND state: ANY("{state.lower()}")',
    )

    docs = rag.invoke(
        input=query,
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
        self.llm = ChatVertexAI(
            model_name=MODEL,
            temperature=0,
            max_tokens=65535,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            # Safety settings to match current implementation.
            safety_settings = {                
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.OFF,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.OFF,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.OFF,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.OFF,
                HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.OFF,
            }
            # Thinking config for Gemini 2.5 Pro.
            # enable_thinking=os.getenv("SHOW_MODEL_THINKING", "false").lower() == "true",
        )

        # Create tools for RAG retrieval.
        self.tools = [retrieve_city_law, retrieve_state_law]

    def create_agent_for_session(self, city: str, state: str) -> CompiledStateGraph:
        """Create an agent instance configured for the user's location.

        Args:
            city: User's city (e.g., "portland", "null")
            state: User's state (e.g., "or")

        Returns:
            AgentExecutor configured with tools and system prompt
        """
        system_prompt = SystemMessage(self.prepare_system_prompt(city, state))

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
            state_schema=TFAAgentState,
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
                "messages": current_query,
                "context": conversation_history,
                "city": city,
                "state": state,
            },
            stream_mode="values",
        ):
            # Extract messages from chunk.
            if "messages" in chunk:
                messages = chunk["messages"]
                if messages and isinstance(messages[-1], AIMessage):
                    yield messages[-1].content  

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
