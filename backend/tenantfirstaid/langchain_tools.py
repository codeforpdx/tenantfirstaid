"""
This module defines Tools for an Agent to call
"""

from pathlib import Path
from pprint import pprint

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool
from langchain_google_community import VertexAISearchRetriever
from pydantic import BaseModel

from .constants import SINGLETON
from .location import city_or_state_input_sanitizer


class _StateLawInputSchema(BaseModel, arbitrary_types_allowed=True):
    query: str
    state: str
    runtime: ToolRuntime


@tool(args_schema=_StateLawInputSchema)
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

    rag = VertexAISearchRetriever(
        name="retrieve_state_law",
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


class _CityLawInputSchema(BaseModel, arbitrary_types_allowed=True):
    query: str
    city: str
    state: str


@tool(args_schema=_CityLawInputSchema)
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

    rag = VertexAISearchRetriever(
        name="retrieve_city_law",
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
