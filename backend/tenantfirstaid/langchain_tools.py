"""
This module defines Tools for an Agent to call
"""

from typing import Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langchain_google_community import VertexAISearchRetriever
from langgraph.config import get_stream_writer
from pydantic import BaseModel

from .constants import LETTER_TEMPLATE, SINGLETON
from .google_auth import load_gcp_credentials
from .location import OregonCity, UsaState


class RagBuilder:
    """
    Helper class to construct a Rag tool from VertexAISearchRetriever
    The helper class handles creds, project, location, datastore, etc.
    """

    __credentials: Credentials | service_account.Credentials
    rag: VertexAISearchRetriever

    def __init__(
        self,
        data_store_id: str,
        filter: str,
        name: Optional[str] = "tfa-retriever",
    ) -> None:
        if SINGLETON.GOOGLE_APPLICATION_CREDENTIALS is None:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set")

        self.__credentials = load_gcp_credentials(
            SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
        )

        self.rag = VertexAISearchRetriever(
            beta=True,  # required for this implementation
            credentials=self.__credentials,
            project_id=SINGLETON.GOOGLE_CLOUD_PROJECT,
            location_id=SINGLETON.GOOGLE_CLOUD_LOCATION,
            data_store_id=data_store_id,
            engine_data_type=0,  # 0 = unstructured; all TFA datastores are unstructured docs
            get_extractive_answers=True,  # TODO: figure out if this is useful
            name=name,
            max_documents=3,
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


@tool
def get_letter_template() -> str:
    """Retrieve the letter template when the user asks to draft or generate a letter.

    Fill in placeholders with any details the user has provided, leave the rest intact.
    After filling in the template, call generate_letter with the completed letter.

    Returns:
        A formatted letter template with placeholder fields.
    """
    return LETTER_TEMPLATE


class GenerateLetterInputSchema(BaseModel):
    letter: str


@tool(args_schema=GenerateLetterInputSchema)
def generate_letter(letter: str) -> str:
    """Display the completed or updated letter in the letter panel.

    Call this after filling in the letter template or after making any updates.

    Args:
        letter: The complete letter content.

    Returns:
        Confirmation that the letter was displayed.
    """
    # Emit a custom chunk so the frontend can render the letter separately from
    # the chat text. See: https://docs.langchain.com/oss/python/langgraph/streaming#use-with-any-llm
    # and https://reference.langchain.com/python/langgraph/config/get_stream_writer
    writer = get_stream_writer()
    writer({"type": "letter", "content": letter})
    return "Letter generated successfully."


class CityStateLawsInputSchema(BaseModel):
    query: str
    state: UsaState
    city: Optional[OregonCity] = None


@tool(args_schema=CityStateLawsInputSchema, response_format="content")
def retrieve_city_state_laws(
    query: str,
    state: UsaState,
    city: Optional[OregonCity] = None,
    *,
    runtime: ToolRuntime,
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

    helper = RagBuilder(
        data_store_id=SINGLETON.VERTEX_AI_DATASTORES["laws"],
        name="retrieve_city_law",
        filter=_filter_builder(city=city, state=state),
    )

    return helper.search(
        query=query,
    )
