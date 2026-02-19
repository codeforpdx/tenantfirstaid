"""
This module defines Tools for an Agent to call
"""

import json
import logging
from pathlib import Path
from typing import Optional

import grpc
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langchain_google_community import VertexAISearchRetriever
from pydantic import BaseModel, Field

from .constants import LETTER_TEMPLATE, SINGLETON
from .location import OregonCity, UsaState

logger = logging.getLogger(__name__)


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
        max_documents: Optional[int] = 3,
        get_extractive_answers: bool = True,
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
                case _ as unknown:
                    raise ValueError(f"Unknown credential type: {unknown!r}")

        self.rag = VertexAISearchRetriever(
            beta=True,  # required for this implementation
            credentials=self.__credentials,
            project_id=SINGLETON.GOOGLE_CLOUD_PROJECT,  # tenantfirstaid
            location_id=SINGLETON.GOOGLE_CLOUD_LOCATION,  # global
            data_store_id=SINGLETON.VERTEX_AI_DATASTORE,  # "tenantfirstaid-corpora_1758844059585",
            engine_data_type=0,  # tenantfirstaid-corpora_1758844059585 is unstructured
            get_extractive_answers=get_extractive_answers,
            name=name,
            max_documents=max_documents,
            filter=filter,
        )

    def search(self, query: str) -> str:
        try:
            docs = self.rag.invoke(input=query)
        except grpc.RpcError as e:
            logger.error("Vertex AI Search unavailable: %s", e)
            return "The legal database is temporarily unavailable. Please try again in a moment."

        if not docs:
            return ""

        parts = []
        for i, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source") or doc.metadata.get("name", "")
            header = f"[Result {i}]" + (f" {source}" if source else "")
            parts.append(f"{header}\n{doc.page_content}")

        return "\n\n".join(parts)


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

    Returns:
        A formatted letter template with placeholder fields.
    """
    return LETTER_TEMPLATE


class CityStateLawsInputSchema(BaseModel):
    query: str
    state: UsaState
    city: Optional[OregonCity] = Field(
        default=None,
        description=(
            "City for city-specific ordinances only (e.g. 'portland', 'eugene')."
            " Omit when querying state statutes (e.g. ORS chapters) — state laws"
            " are indexed separately and will not appear in city-filtered results."
        ),
    )
    max_documents: int = Field(
        default=3,
        ge=1,
        le=10,
        description=(
            "Number of documents to retrieve. Increase beyond 5 if initial results"
            " are incomplete, truncated, or not relevant to the query."
        ),
    )
    get_extractive_answers: bool = Field(
        default=True,
        description=(
            "When True, returns short targeted snippets. Set to False to retrieve"
            " broader document chunks — use this when results only contain"
            " cross-references to a statute (e.g. 'pursuant to ORS 90.260') rather"
            " than the statute text itself, or when snippets are too brief."
        ),
    )


@tool(args_schema=CityStateLawsInputSchema, response_format="content")
def retrieve_city_state_laws(
    query: str,
    state: UsaState,
    city: Optional[OregonCity] = None,
    max_documents: int = 3,
    get_extractive_answers: bool = True,
    *,
    runtime: ToolRuntime,
) -> str:
    """
    Retrieve relevant state (and when specified, city) specific housing
    laws from the RAG corpus.

    Args:
        query: The user's legal question
        city: The user's city for city-specific ordinances only (e.g., "portland",
            "eugene"). Omit when looking up state statutes (e.g. ORS chapters) —
            state laws are indexed separately and will not appear in city-filtered
            results.
        state: The user's state (e.g., "or")
        max_documents: Number of documents to retrieve (1-10). Increase to 3-5
            if initial results are incomplete or truncated.
        get_extractive_answers: When True, returns short targeted snippets.
            Set to False to retrieve broader document chunks when snippets
            are too brief.

    Returns:
        Relevant legal passages from city- or state-specific housing laws.
    """

    helper = Rag_Builder(
        name="retrieve_city_law",
        max_documents=max_documents,
        get_extractive_answers=get_extractive_answers,
        filter=__filter_builder(city=city, state=state),
    )

    return helper.search(
        query=query,
    )
