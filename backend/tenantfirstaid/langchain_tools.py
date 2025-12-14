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


class Rag_Builder:
    """
    Helper class to construct a Rag tool from VertexAISearchRetriever
    The helper class handles creds, project, location, datastore, etc.
    """

    __credentials: Credentials
    rag: VertexAISearchRetriever

    def __init__(
        self,
        filter: str,
        name: Optional[str] = "tfa-retriever",
        max_documents: Optional[int] = 5,
    ) -> None:
        self.__credentials = Credentials.from_authorized_user_file(
            SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
        )

        self.rag = VertexAISearchRetriever(
            beta=True,  # required for this implementation
            credentials=self.__credentials,
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


def __filter_builder(state: UsaState, city: Optional[OregonCity] = None) -> str:
    if city is None:
        city_or_null = "null"
    else:
        city_or_null = city.lower()

    return f"""city: ANY("{city_or_null}") AND state: ANY("{state.lower()}")"""


class CityStateLawsInputSchema(BaseModel):
    query: str
    city: Optional[OregonCity]
    state: UsaState


@tool(args_schema=CityStateLawsInputSchema)
def retrieve_city_state_laws(
    query: str, city: Optional[OregonCity], state: UsaState, runtime: ToolRuntime
) -> str:
    """
    Retrieve relevant state (and when specified, city) specific housing
    laws from the RAG corpus.

    Args:
        query: The user's legal question
        city: The user's city (e.g., "portland", "eugene"), optional
        state: The user's state (e.g., "or")

    Returns:
        Relevant legal passages from city-specific laws
    """

    helper = Rag_Builder(
        name="retrieve_city_law",
        max_documents=5,
        filter=__filter_builder(city=city, state=state),
    )

    return helper.search(
        query=query,
    )
