"""
This module defines Tools for an Agent to call
"""

import logging
from typing import Callable, Optional, Type, cast

import httpx
from google.api_core import exceptions as google_exceptions
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from langchain_core.tools import BaseTool, tool
from langchain_google_community import VertexAISearchRetriever
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .constants import (
    LETTER_TEMPLATE,
    SINGLETON,
    DatastoreKey,
)
from .google_auth import load_gcp_credentials
from .location import OregonCity, UsaState

logger = logging.getLogger(__name__)


def _repair_mojibake(text: str) -> str:
    """Attempt to repair UTF-8 text that was incorrectly decoded as Latin-1.

    Vertex AI may return corpus text with mojibake (e.g. â€™ instead of ')
    if the source document's UTF-8 encoding was misread as Latin-1 at index
    time. This reverses that by re-encoding as Latin-1 and decoding as UTF-8.

    Logs a warning if the repair itself appears to corrupt the text (i.e. the
    round-trip fails or introduces replacement characters).
    """
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        # Round-trip failure means the text has non-ASCII characters that are
        # not the result of UTF-8-as-Latin-1 mojibake (e.g. bare § U+00A7 from
        # a dropped 0xC2 byte). Correct behaviour — leave the text alone.
        char = (
            repr(text[e.start]) if hasattr(e, "start") and e.start < len(text) else "?"
        )
        logger.debug(
            "mojibake repair skipped — round-trip failed at pos %s (char %s): %.120r",
            getattr(e, "start", "?"),
            char,
            text,
        )
        return text

    if repaired != text:
        logger.debug(
            "mojibake repair applied to RAG passage (first 120 chars): %.120r", text
        )

    return repaired


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
        max_documents: int = 3,
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
            # Suggestion-only: spell corrections are recorded in the response but the
            # original query is used for retrieval. Prevents auto-correction from
            # mangling ORS references and other legal terminology.
            spell_correction_mode=1,
            name=name,
            max_documents=max_documents,
            filter=filter,
        )

    @retry(
        retry=retry_if_exception_type(
            (httpx.ReadError, google_exceptions.ServiceUnavailable)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
        before_sleep=lambda rs: logger.warning(
            "RAG search retry #%d after %s", rs.attempt_number, rs.outcome.exception()
        ),
    )
    def search(self, query: str) -> str:
        docs = self.rag.invoke(
            input=query,
        )

        return "\n".join([_repair_mojibake(doc.page_content) for doc in docs])


def _filter_builder(state: UsaState, city: Optional[OregonCity] = None) -> str:
    if city is None:
        city_filter = 'city: ANY("null")'
    else:
        # Include both city-specific and state-level ("null") documents so the
        # agent sees both layers of law in a single retrieval.
        city_filter = f'city: ANY("{city.lower()}", "null")'

    return f"""{city_filter} AND state: ANY("{state.lower()}")"""


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
    Letter content must always be passed to this tool — never output letter
    content directly as text, as doing so will break the UI.

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
    max_documents: int = Field(
        default=3,
        ge=1,
        le=8,
        description="""Number of passages to retrieve (1–8). Use a smaller value
                       (3–5) for focused questions. Use a larger value (6–8) when
                       the question spans multiple topics or an initial retrieval
                       missed the relevant passage.""",
    )


class CityStateLawsInputSchema(BaseModel):
    query: str = Field(
        description="""A precise legal search query for the specific legal issue.
                       Rephrase the user's question using relevant legal terms and
                       ORS references when applicable (e.g. 'week-to-week tenancy
                       nonpayment notice timing ORS 90.394'). Avoid paraphrasing so
                       broadly that specific statutory details are lost.

                       Frame queries around the legal relationship and direction of
                       obligation: who is required, entitled, or prohibited to do what
                       (e.g. 'landlord required to pay interest on security deposit'
                       rather than 'landlord security deposit interest'). On retry
                       after a miss, change the framing angle — try the other party's
                       perspective or restate as an obligation/entitlement — rather
                       than repeating the same terms with an ORS number appended.
                       Always include the specific action being contested in the query
                       (e.g. 'landlord required to pay interest' not just 'landlord
                       obligation security deposit')."""
    )
    state: UsaState
    city: Optional[OregonCity] = None
    max_documents: int = Field(
        default=5,
        ge=1,
        le=8,  # Total number of documents in the laws datastore.
        description="""Number of passages to retrieve (1–8). Use a smaller value
                       (3–5) for focused questions with a clear statutory target.
                       Use a larger value (6–8) when the question spans multiple
                       statutes, involves city overrides, or an initial retrieval
                       missed the relevant passage.""",
    )
    max_extractive_answer_count: int = Field(
        default=1,
        ge=1,
        le=5,
        description="""Extractive answers per document (1–5). Each is a short
                       passage the search engine identifies as directly relevant.
                       Increase on retry if the first search returned passages
                       from the right document but missed the specific subsection
                       you need.""",
    )
    max_extractive_segment_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="""Extractive segments per document (1–10). Segments are
                       longer surrounding blocks of text that provide more context
                       than answers. Increase on retry when the answer likely sits
                       adjacent to what was returned (e.g. the right ORS section
                       was found but a neighboring subsection was missed).""",
    )


def _default_filter_from_city_state(**kwargs: object) -> str:
    """Adapter that extracts state/city from tool kwargs and calls _filter_builder.

    All other kwargs (query, max_documents, etc.) are intentionally ignored;
    custom filter_builders may use them if needed.
    """
    return _filter_builder(
        state=cast(UsaState, kwargs["state"]),
        city=cast(Optional[OregonCity], kwargs.get("city")),
    )


def _make_rag_tool(
    datastore_key: DatastoreKey,
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
        # Strip non-schema kwargs injected by LangChain (e.g. runtime) and
        # validate to populate Field defaults for any omitted optional fields.
        schema_data = {k: v for k, v in kwargs.items() if k in args_schema.model_fields}
        validated = args_schema.model_validate(schema_data).model_dump()
        rag_filter = filter_builder(**validated) if filter_builder is not None else None
        helper = RagBuilder(
            data_store_id=SINGLETON.VERTEX_AI_DATASTORES[datastore_key],
            name=tool_name,
            filter=rag_filter,
            max_documents=validated["max_documents"],
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
RAG_TOOL_REGISTRY: list[tuple[DatastoreKey, BaseTool]] = [
    (DatastoreKey.LAWS, retrieve_city_state_laws),
    # Uncomment when VERTEX_AI_DATASTORE_OREGON_LAW_HELP is configured and needed for new tooling.
    # (DatastoreKey.OREGON_LAW_HELP, retrieve_oregon_law_help),
]


def get_active_rag_tools() -> list[BaseTool]:
    """Return tools whose backing datastore is present in the environment."""
    return [t for key, t in RAG_TOOL_REGISTRY if key in SINGLETON.VERTEX_AI_DATASTORES]
