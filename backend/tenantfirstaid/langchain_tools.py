"""
This module defines Tools for an Agent to call
"""

from typing import Optional

from google.oauth2.credentials import Credentials
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langchain_google_community import VertexAISearchRetriever
from pydantic import BaseModel

from .constants import SINGLETON
from .location import OregonCity, UsaState


class _Rag_Builder:
    """
    Helper class to construct a Rag tool from VertexAISearchRetriever
    The helper class handles creds, project, location, datastore, etc.
    """

    credentials: Credentials
    rag: VertexAISearchRetriever

    def __init__(
        self,
        filter: str,
        name: Optional[str] = "tfa-retriever",
        max_documents: Optional[int] = 5,
    ) -> None:
        self.credentials = Credentials.from_authorized_user_file(
            SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
        )

        self.rag = VertexAISearchRetriever(
            beta=True,  # required for this implementation
            credentials=self.credentials,
            project_id=SINGLETON.GOOGLE_CLOUD_PROJECT,  # tenantfirstaid
            location_id=SINGLETON.GOOGLE_CLOUD_LOCATION,  # global
            data_store_id=SINGLETON.VERTEX_AI_DATASTORE,  # "tenantfirstaid-corpora_1758844059585",
            engine_data_type=0,  # tenantfirstaid-corpora_1758844059585 is unstructured
            get_extractive_answers=True,  # TODO: figure out if this is useful
            name=name,
            max_documents=max_documents,
            filter=filter,
        )

    def search(self, query: str) -> str:
        docs = self.rag.invoke(
            input=query,
        )

        return "\n".join([doc.page_content for doc in docs])


def _filter_builder(state: UsaState, city: Optional[OregonCity] = None) -> str:
    if city is None:
        city_or_null = "null"
    else:
        city_or_null = city.lower()

    return f"""city: ANY("{city_or_null}") AND state: ANY("{state.lower()}")"""


class _StateLawInputSchema(BaseModel, arbitrary_types_allowed=True):
    query: str
    state: UsaState


@tool(args_schema=_StateLawInputSchema)
def retrieve_state_law(query: str, state: UsaState, runtime: ToolRuntime) -> str:
    """Retrieve state-wide housing laws from the RAG corpus.

    Use this tool for general state law questions or when city is not specified.

    Args:
        query: The user's legal question
        state: The user's state (e.g., "or")
        runtime: Tool runtime context

    Returns:
        Relevant legal passages from state laws
    """

    helper = _Rag_Builder(
        name="retrieve_state_law",
        filter=_filter_builder(state=state),
        max_documents=5,
    )

    return helper.search(
        query=query,
    )


class _CityLawInputSchema(BaseModel):
    query: str
    city: Optional[OregonCity]
    state: UsaState


@tool(args_schema=_CityLawInputSchema)
def retrieve_city_law(query: str, city: Optional[OregonCity], state: UsaState) -> str:
    """Retrieve city-specific housing laws from the RAG corpus.

    Use this tool when the user has specified their city location.

    Args:
        query: The user's legal question
        city: The user's city (e.g., "portland", "eugene")
        state: The user's state (e.g., "or")

    Returns:
        Relevant legal passages from city-specific laws
    """

    helper = _Rag_Builder(
        name="retrieve_city_law",
        max_documents=5,
        filter=_filter_builder(city=city, state=state),
    )

    return helper.search(
        query=query,
    )
