"""
This module defines Tools for an Agent to call
"""

from typing import Callable, Optional, Type, cast

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from langchain_core.tools import BaseTool, tool
from langchain_google_community import VertexAISearchRetriever
from langgraph.config import get_stream_writer
from pydantic import BaseModel

from .constants import (
    LETTER_TEMPLATE,
    SINGLETON,
    DatastoreKey,
)
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
        name: Optional[str] = "tfa-retriever",
        filter: Optional[str] = None,
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


class QueryOnlyInputSchema(BaseModel):
    query: str


class CityStateLawsInputSchema(BaseModel):
    query: str
    state: UsaState
    city: Optional[OregonCity] = None


def _default_filter_from_city_state(**kwargs: object) -> str:
    """Adapter that extracts state/city from tool kwargs and calls _filter_builder."""
    # query is intentionally not forwarded; custom filter_builders may use it.
    return _filter_builder(
        state=cast(UsaState, kwargs["state"]),
        city=cast(Optional[OregonCity], kwargs.get("city")),
    )


def _make_rag_tool(
    datastore_key: str,
    tool_name: str,
    description: str,
    *,
    args_schema: Type[BaseModel],
    filter_builder: Optional[Callable[..., str]] = None,
) -> BaseTool:
    """Factory that creates a RAG retrieval tool bound to a specific datastore."""

    @tool(
        tool_name,
        description=description,
        args_schema=args_schema,
        response_format="content",
    )
    def _retrieve(**kwargs: object) -> str:
        # Strip non-schema kwargs injected by LangChain (e.g. runtime).
        schema_data = {k: v for k, v in kwargs.items() if k in args_schema.model_fields}
        # Validate against the schema to populate any optional field defaults.
        validated = args_schema.model_validate(schema_data).model_dump()
        rag_filter = filter_builder(**validated) if filter_builder is not None else None
        helper = RagBuilder(
            data_store_id=SINGLETON.VERTEX_AI_DATASTORES[datastore_key],
            name=tool_name,
            filter=rag_filter,
        )
        return helper.search(query=validated["query"])

    return _retrieve


retrieve_city_state_laws: BaseTool = _make_rag_tool(
    DatastoreKey.LAWS,
    "retrieve_city_state_laws",
    "Retrieve relevant state (and when specified, city) specific housing laws from the RAG corpus.",
    args_schema=CityStateLawsInputSchema,
    filter_builder=_default_filter_from_city_state,
)

# Defined here for testability; inactive until added to RAG_TOOL_REGISTRY and
# VERTEX_AI_DATASTORE_OREGON_LAW_HELP is configured.
retrieve_oregon_law_help: BaseTool = _make_rag_tool(
    DatastoreKey.OREGON_LAW_HELP,
    "retrieve_oregon_law_help",
    (
        "Retrieve relevant housing law information from the OregonLawHelp RAG corpus."
        " Use this alongside retrieve_city_state_laws to broaden coverage with"
        " plain-language guidance from OregonLawHelp.org."
    ),
    args_schema=QueryOnlyInputSchema,
)

# Registry of (datastore_key, tool) pairs. Multiple tools may share the same
# datastore key; each tool is included only when its datastore is configured.
RAG_TOOL_REGISTRY: list[tuple[str, BaseTool]] = [
    (DatastoreKey.LAWS, retrieve_city_state_laws),
    # Uncomment when VERTEX_AI_DATASTORE_OREGON_LAW_HELP is configured and needed for new tooling.
    # (DatastoreKey.OREGON_LAW_HELP, retrieve_oregon_law_help),
]


def get_active_rag_tools() -> list[BaseTool]:
    """Return tools whose backing datastore is present in the environment."""
    return [t for key, t in RAG_TOOL_REGISTRY if key in SINGLETON.VERTEX_AI_DATASTORES]
