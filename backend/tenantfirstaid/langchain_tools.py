"""
This module defines Tools for an Agent to call
"""

import json
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langchain_google_community import VertexAISearchRetriever
from pydantic import BaseModel

from .constants import LETTER_TEMPLATE, SINGLETON
from .location import OregonCity, UsaState


class Rag_Builder:
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
        max_documents: Optional[int] = 1,
    ) -> None:
        if SINGLETON.GOOGLE_APPLICATION_CREDENTIALS is None:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is not set")

        cred_path = Path(SINGLETON.GOOGLE_APPLICATION_CREDENTIALS)

        with cred_path.open("r") as f:
            match json.load(f).get("type"):
                case "authorized_user":
                    self.__credentials = Credentials.from_authorized_user_file(
                        SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
                    )
                case "service_account":
                    self.__credentials = (
                        service_account.Credentials.from_service_account_file(
                            SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
                        )
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
def generate_letter(_letter: str) -> str:
    """Display the completed or updated letter in the letter panel.

    Call this after filling in the letter template or after making any updates.

    Args:
        letter: The complete letter content.

    Returns:
        Confirmation that the letter was displayed.
    """
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

    helper = Rag_Builder(
        name="retrieve_city_law",
        max_documents=1,
        filter=__filter_builder(city=city, state=state),
    )

    return helper.search(
        query=query,
    )
