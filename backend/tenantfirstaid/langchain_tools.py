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


def repair_mojibake(text: str) -> str:
    """Attempt to repair UTF-8 text that was incorrectly decoded as Latin-1.

    Vertex AI may return corpus text with mojibake (e.g. â€™ instead of ')
    if the source document's UTF-8 encoding was misread as Latin-1 at index
    time. This reverses that by re-encoding as Latin-1 and decoding as UTF-8.
    Logs a warning if the repair itself appears to corrupt the text.

    Args:
        text: Text potentially containing UTF-8-as-Latin-1 mojibake.

    Returns:
        Repaired text, or original text if repair failed or was unnecessary.
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
    """Helper class to construct a RAG retrieval tool from Vertex AI Search.

    Manages GCP credentials, project/location/datastore configuration, and query
    parameters for the VertexAISearchRetriever. Handles UTF-8 mojibake repair on
    retrieved passages.
    """

    __credentials: Credentials | service_account.Credentials
    """GCP credentials loaded from SINGLETON."""
    rag: VertexAISearchRetriever
    """Configured Vertex AI Search retriever."""

    def __init__(
        self,
        data_store_id: str,
        name: Optional[str] = "tfa-retriever",
        filter: Optional[str] = None,
        max_documents: int = 3,
        *,
        get_extractive_answers: bool = False,
        max_extractive_answer_count: int = 1,
        max_extractive_segment_count: int = 3,
    ) -> None:
        """Initialize the RAG builder with a datastore and retrieval parameters.

        Args:
            data_store_id: Vertex AI Search datastore ID.
            name: Tool name for logging (default ``tfa-retriever``).
            filter: Vertex AI Search filter string for document metadata.
            max_documents: Maximum documents to retrieve (default 3).
            get_extractive_answers: Prefer extractive answers over segments (default False).
            max_extractive_answer_count: Max extractive answers per document.
            max_extractive_segment_count: Max extractive segments per document.
        """
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
            # Default to extractive segments rather than answers. Extractive answers
            # are short, individually selected sentences that, for statutory queries,
            # tend to surface annotation/case-note lines that lexically match the
            # query (e.g. "duty to mitigate damages" from NOTES OF DECISIONS) while
            # the operative statutory text — which lives in longer segments — is
            # never returned. Segments return the surrounding block, so the citable
            # subsection text (e.g. ORS 90.410(3), ORS 90.302(2)(e)) comes through.
            get_extractive_answers=get_extractive_answers,
            max_extractive_answer_count=max_extractive_answer_count,
            max_extractive_segment_count=max_extractive_segment_count,
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
            "RAG search retry #%d after %s",
            rs.attempt_number,
            rs.outcome.exception() if rs.outcome else None,
        ),
    )
    def search(self, query: str) -> str:
        """Execute a RAG search with automatic retry on transient errors.

        Queries the Vertex AI Search retriever with mojibake repair applied to each
        retrieved passage. Retries up to 3 times on read errors or service unavailability.

        Args:
            query: Legal search query.

        Returns:
            Newline-joined concatenation of retrieved document passages.
        """
        docs = self.rag.invoke(
            input=query,
        )

        return "\n".join([repair_mojibake(doc.page_content) for doc in docs])


def filter_builder(state: UsaState, city: Optional[OregonCity] = None) -> str:
    """Build a Vertex AI Search filter string for the given state and optional city.

    City-scoped queries include both city-specific and state-level ("null") documents
    so the agent sees both layers of law in a single retrieval.

    Args:
        state: User's [state](`~location.UsaState`).
        city: User's [city](`~location.OregonCity`), optional.

    Returns:
        Vertex AI Search filter string for document metadata.
    """
    if city is None:
        city_filter = 'city: ANY("null")'
    else:
        # Include both city-specific and state-level ("null") documents so the
        # agent sees both layers of law in a single retrieval.
        city_filter = f'city: ANY("{city.lower()}", "null")'

    return f"""{city_filter} AND state: ANY("{state.lower()}")"""


@tool
def get_letter_template() -> str:
    """Retrieve the letter template for drafting or generating a letter.

    Fill in placeholders with any details the user has provided, leaving the rest
    intact. After filling in the template, call generate_letter with the completed
    letter.

    Returns:
        A formatted letter template with placeholder fields.
    """
    return LETTER_TEMPLATE


class GenerateLetterInputSchema(BaseModel):
    """Input schema for the generate_letter tool.

    Accepts the completed letter content to display in the letter panel.
    """

    letter: str
    """The complete letter content."""


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
    """Input schema for RAG retrieval without location filtering.

    Used by datastores that don't require location context (e.g., OregonLawHelp).
    """

    query: str
    """Legal search query."""
    max_documents: int = Field(
        default=3,
        ge=1,
        le=8,
        description="""Number of passages to retrieve (1–8). Use a smaller value
                       (3–5) for focused questions. Use a larger value (6–8) when
                       the question spans multiple topics or an initial retrieval
                       missed the relevant passage.""",
    )
    """Maximum documents to retrieve."""


class CityStateLawsInputSchema(BaseModel):
    """Input schema for city/state-aware RAG retrieval.

    Accepts a legal query and location (state and optional city), with tunable
    retrieval parameters. The agent uses this to retrieve Oregon housing law
    with optional city-specific overrides.
    """

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
    """Precise legal search query."""
    state: UsaState
    """User's state."""
    city: Optional[OregonCity] = None
    """User's city, optional."""
    max_documents: int = Field(
        default=3,
        ge=1,
        le=8,
        description="""Number of passages to retrieve (1–8). Use a smaller value
                       (3–5) for focused questions with a clear statutory target.
                       Use a larger value (6–8) when the question spans multiple
                       statutes, involves city overrides, or an initial retrieval
                       missed the relevant passage.""",
    )
    """Maximum documents to retrieve."""
    max_extractive_segment_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="""Extractive segments per document (1–10). Segments are
                       blocks of statutory text returned with their surrounding
                       context — this is how the operative subsection text (e.g. a
                       specific ORS paragraph) is surfaced. Increase on retry when
                       the right ORS section was found but the specific subsection
                       you need sits adjacent to what was returned.""",
    )
    """Extractive segments per document."""


def _default_filter_from_city_state(**kwargs: object) -> str:
    """Extract state/city from tool kwargs and build a Vertex AI Search filter string.

    All other kwargs (query, max_documents, etc.) are intentionally ignored;
    custom filter_builders may use them if needed.

    Args:
        **kwargs: Tool kwargs containing at minimum `state` ([`UsaState`](`~location.UsaState`)) and optionally `city` ([`OregonCity`](`~location.OregonCity`)).

    Returns:
        Vertex AI Search filter string for document metadata.
    """
    return filter_builder(
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
    """Factory that creates a RAG retrieval tool for a specific Vertex AI datastore.

    Args:
        datastore_key: Enum key to look up the datastore ID in SINGLETON.
        tool_name: Name of the tool (shown to the model).
        description: Tool description for the model.
        args_schema: Pydantic model defining tool parameters and validation.
        filter_builder: Optional function to build filter strings from kwargs.

    Returns:
        A LangChain BaseTool wrapping the RAG query logic.
    """

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
        # Forward extractive-count knobs when the schema exposes them. These were
        # previously validated but silently dropped, so the model's documented
        # "increase on retry" guidance had no effect. RagBuilder defaults cover
        # schemas that omit them (e.g. QueryOnlyInputSchema).
        extractive_kwargs = {
            k: validated[k]
            for k in ("max_extractive_answer_count", "max_extractive_segment_count")
            if k in validated
        }
        helper = RagBuilder(
            data_store_id=SINGLETON.VERTEX_AI_DATASTORES[datastore_key],
            name=tool_name,
            filter=rag_filter,
            max_documents=validated["max_documents"],
            **extractive_kwargs,
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
"""RAG retrieval tool for the Laws datastore, with state/city filtering and extractive segment support.
   This is the primary RAG tool used in production for housing law queries."""

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
"""RAG retrieval tool for the OregonLawHelp datastore, with query-only input schema.
   This is an optional RAG tool that can be added to the agent when VERTEX_AI_DATASTORE_OREGON_LAW_HELP is configured. It provides plain-language guidance from OregonLawHelp.org alongside the statutory retrieval from retrieve_city_state_laws."""

RAG_TOOL_REGISTRY: list[tuple[DatastoreKey, BaseTool]] = [
    (DatastoreKey.LAWS, retrieve_city_state_laws),
    # Uncomment when VERTEX_AI_DATASTORE_OREGON_LAW_HELP is configured and needed for new tooling.
    # (DatastoreKey.OREGON_LAW_HELP, retrieve_oregon_law_help),
]
"""Registry of (datastore_key, tool) pairs. Multiple tools may share the same
   datastore key; each tool is included only when its datastore is configured.
"""


def get_active_rag_tools() -> list[BaseTool]:
    """Return RAG retrieval tools whose datastores are configured.

    Filters :data:`RAG_TOOL_REGISTRY` to include only tools whose datastore IDs
    are present in the environment, allowing optional datastores to be omitted.

    Returns:
        List of active RAG tools to be added to the agent.
    """
    return [t for key, t in RAG_TOOL_REGISTRY if key in SINGLETON.VERTEX_AI_DATASTORES]
