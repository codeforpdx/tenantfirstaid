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
from pydantic import BaseModel, Field

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
        filter: str,
        name: Optional[str] = "tfa-retriever",
        max_documents: Optional[int] = 3,
    ) -> None:
        if SINGLETON.GOOGLE_APPLICATION_CREDENTIALS is None:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set")

        self.__credentials = load_gcp_credentials(
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
            # Suggestion-only: spell corrections are recorded in the response but the
            # original query is used for retrieval. Prevents auto-correction from
            # mangling ORS references and other legal terminology.
            spell_correction_mode=1,
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
    query: str = Field(
        description="""A precise legal search query for the specific legal issue.
                       Rephrase the user's question using relevant legal terms and
                       ORS references when applicable (e.g. 'week-to-week tenancy
                       nonpayment notice timing ORS 90.394'). Avoid paraphrasing so
                       broadly that specific statutory details are lost."""
    )
    state: UsaState
    city: Optional[OregonCity] = None
    max_documents: int = Field(
        default=5,
        ge=1,
        le=25,
        description="""Number of passages to retrieve (1–15). Use a smaller value
                       (3–5) for focused questions with a clear statutory target.
                       Use a larger value (10–15) when the question spans multiple
                       statutes, involves city overrides, or an initial retrieval
                       missed the relevant passage.""",
    )


@tool(args_schema=CityStateLawsInputSchema, response_format="content")
def retrieve_city_state_laws(
    query: str,
    state: UsaState,
    city: Optional[OregonCity] = None,
    max_documents: int = 5,
    *,
    runtime: ToolRuntime,
) -> str:
    """
    Retrieve relevant state (and when specified, city) specific housing
    laws from the RAG corpus.

    Args:
        query: A precise legal search query for the specific legal issue
        city: The user's city (e.g., "portland", "eugene"), optional
        state: The user's state (e.g., "or")
        max_documents: Number of passages to retrieve (1–15)

    Returns:
        Relevant legal passages from city-specific laws
    """

    helper = RagBuilder(
        name="retrieve_city_law",
        max_documents=max_documents,
        filter=_filter_builder(city=city, state=state),
    )

    return helper.search(
        query=query,
    )
