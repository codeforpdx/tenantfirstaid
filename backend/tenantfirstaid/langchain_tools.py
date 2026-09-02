"""
This module defines Tools for an Agent to call
"""

import json
import logging
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Callable, Literal, Optional, Type, cast

import httpx
from google.api_core import exceptions as google_exceptions
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from langchain_core.tools import BaseTool, tool
from langchain_google_community import VertexAISearchRetriever
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field, field_validator
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
from .referrals import REFERRALS

_LEGAL_AID_REFERRALS_JSON: str = json.dumps(
    [r.model_dump(mode="json", exclude_none=True) for r in REFERRALS]
)

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


@tool
def get_legal_aid_referrals() -> str:
    """Retrieve the catalog of Oregon legal-aid and tenant-services referral organizations.

    Call this when a tenant asks for a lawyer, legal aid, or somewhere to get
    help beyond this chat. Use the returned fields (service_types,
    provider_types, geographic_scope, case_stages, hours) to recommend the
    organization(s) that best match the tenant's situation and location.

    Returns:
        A JSON array of referral records.
    """
    return _LEGAL_AID_REFERRALS_JSON


class NoticeServiceMethod(StrEnum):
    """Methods of serving a written notice under ORS 90.155(1) and (5).

    Scope note: this models ORS 90.155/90.160 only — the primary service-and-timing
    framework for landlord/tenant notices. It does not model ORS 90.150(3) (when a
    mailed notice counts as "served" for actual-notice-equivalence purposes) or any
    notice type that supplies its own delivery rule (e.g. ORS 90.425 abandoned
    personal property, ORS 90.300(14) security deposit accountings).
    """

    PERSONAL_DELIVERY = "personal_delivery"
    """ORS 90.155(1)(a): personal delivery to the landlord or tenant. No extension, no special clock start."""

    FIRST_CLASS_MAIL = "first_class_mail"
    """ORS 90.155(1)(b): first-class mail alone. Adds the ORS 90.155(2) three-day extension."""

    MAIL_AND_ATTACH = "mail_and_attach"
    """ORS 90.155(1)(c): first-class mail AND attachment to a designated location. Valid
    only if the written rental agreement authorizes it. No 90.155(2) extension — instead,
    an hour-based termination notice gets the ORS 90.160(2)(b) 11:59 PM clock start."""

    EMAIL_AND_MAIL = "email_and_mail"
    """ORS 90.155(5): first-class mail AND e-mail, required for a notice terminating the
    tenancy served by e-mail. Valid only under a signed ORS 90.155(1)(d) addendum. No
    90.155(2) extension — instead gets the ORS 90.160(2)(b) 11:59 PM clock start."""

    EMAIL_ONLY = "email_only"
    """ORS 90.155(1)(d): e-mail alone. Valid only under a signed addendum, and only for a
    notice that does NOT terminate the tenancy — e-mail alone never validly serves a
    termination notice (ORS 90.155(5))."""


class NoticeDeadlineInputSchema(BaseModel):
    """Input schema for the calculate_ors_90_160_notice_deadline tool."""

    service_date: date = Field(
        description="""The date the notice was served. For mail_and_attach or
        email_and_mail, this is the date BOTH methods were completed."""
    )
    service_time: Optional[time] = Field(
        default=None,
        description="""Clock time the notice was served, 24-hour or 12-hour form (e.g.
        "14:30" or "2:30 PM"). Required when period_unit is "hours", UNLESS
        is_termination_notice is true and service_method is mail_and_attach or
        email_and_mail — those start the clock at 11:59 PM regardless of what time
        service actually happened.""",
    )
    period_value: int = Field(
        gt=0,
        description="""The number IN period_unit's UNIT — e.g. 72 for a "72-hour"
        notice, 30 for a "30-day" notice. Copy this directly off the statute governing
        the notice. Do not convert it to the other unit yourself; pass it as written and
        set period_unit to match.""",
    )
    period_unit: Literal["hours", "days"] = Field(
        description="""Whether period_value counts HOURS or DAYS. Must match the
        statute's own wording exactly (a "72-hour notice" is period_unit="hours", a
        "30-day notice" is period_unit="days") — never infer or convert this."""
    )
    service_method: NoticeServiceMethod = Field(
        description="""How the notice was served, under ORS 90.155(1) or (5):
        personal_delivery — no extension, no special clock start. first_class_mail —
        mail alone; adds the ORS 90.155(2) three-day extension. mail_and_attach —
        mail AND attachment to a designated location, valid only if the written
        rental agreement authorizes it; no 90.155(2) extension, but an hour-based
        termination notice gets the ORS 90.160(2)(b) 11:59 PM clock start instead.
        email_and_mail — mail AND e-mail, REQUIRED (not optional) for a termination
        notice served by e-mail under ORS 90.155(5), valid only under a signed
        addendum; same 11:59 PM clock start as mail_and_attach, no 90.155(2)
        extension. email_only — e-mail alone, valid only under a signed addendum
        and ONLY for a notice that does not terminate the tenancy — e-mail alone
        never validly serves a termination notice.""",
    )
    is_termination_notice: bool = Field(
        description="""True if this notice terminates the tenancy, False if it does not.
        Required — this is never a safe default to guess, since it silently changes
        which statutory clock-start rule applies. If it isn't already established, ask
        the tenant whether the notice ends the tenancy before calling this tool. Governs
        whether the ORS 90.155(5) mail+e-mail requirement and the ORS 90.160(2)(b) 11:59
        PM clock start apply.""",
    )

    @field_validator("service_time", mode="before")
    @classmethod
    def _parse_service_time(cls, v: object) -> object:
        """Accept 12-hour clock strings ("2:30 PM") in addition to 24-hour/ISO.

        Pydantic's built-in `time` parsing only understands 24-hour/ISO-8601
        strings, but the field description invites 12-hour input, which is
        what LLM callers naturally produce.
        """
        if isinstance(v, str):
            for fmt in ("%I:%M %p", "%I:%M%p", "%I %p"):
                try:
                    return datetime.strptime(v.strip(), fmt).time()
                except ValueError:
                    continue
        return v


@tool(args_schema=NoticeDeadlineInputSchema, response_format="content")
def calculate_ors_90_160_notice_deadline(
    service_date: date,
    period_value: int,
    period_unit: Literal["hours", "days"],
    service_method: NoticeServiceMethod,
    service_time: Optional[time] = None,
    is_termination_notice: bool = False,
) -> str:
    """Compute the exact deadline of an Oregon landlord-tenant notice period.

    Call this instead of doing the date/time math by hand — ORS 90.160's hour-vs-day
    counting rules, the ORS 90.155(2) mail extension, and the ORS 90.155(1)(c)/(5)
    mail-and-attach/e-mail-and-mail clock start are easy to mix up, and mixing up hours
    with days produces a deadline that's off by roughly a factor of 24.

    Args:
        service_date: Date the notice was served (or, for mail_and_attach/email_and_mail,
            the date both methods were completed).
        period_value: The notice period's length, in period_unit's unit.
        period_unit: "hours" or "days" — must match the governing statute exactly.
        service_method: How the notice was served, under ORS 90.155(1) or (5).
        service_time: Clock time of service. Required for hour-based periods unless the
            ORS 90.160(2)(b) special start applies (see is_termination_notice).
        is_termination_notice: True if the notice terminates the tenancy.

    Returns:
        A formatted result giving the computed deadline, its statutory basis, and an
        explicit hours-vs-days check — relay it to the tenant as given, don't recompute.
    """
    if service_method == NoticeServiceMethod.EMAIL_ONLY and is_termination_notice:
        return (
            "SERVICE INVALID, NO DEADLINE COMPUTED: e-mail alone can never validly "
            "serve a notice terminating the tenancy — ORS 90.155(5) requires BOTH "
            "first-class mail AND e-mail for a termination notice sent by e-mail. Tell "
            "the tenant this service was defective; do not compute or state a deadline "
            "for it. If the notice was also sent by first-class mail, call this tool "
            "again with service_method=email_and_mail."
        )
    if (
        service_method == NoticeServiceMethod.EMAIL_AND_MAIL
        and not is_termination_notice
    ):
        return (
            "INPUT MISMATCH, NO DEADLINE COMPUTED: email_and_mail models ORS 90.155(5), "
            "which only applies to notices terminating the tenancy. If this notice "
            "terminates the tenancy, call again with is_termination_notice=true. "
            "Otherwise, for a non-termination notice sent by e-mail, use "
            "service_method=email_only."
        )

    mail_extension_applies = service_method == NoticeServiceMethod.FIRST_CLASS_MAIL
    special_hour_start = is_termination_notice and service_method in (
        NoticeServiceMethod.MAIL_AND_ATTACH,
        NoticeServiceMethod.EMAIL_AND_MAIL,
    )

    if period_unit == "days":
        # ORS 90.160(1): consecutive calendar days, excluding the day of service,
        # including the last day through 11:59 PM.
        total_days = period_value + (3 if mail_extension_applies else 0)
        deadline = datetime.combine(
            service_date + timedelta(days=total_days), time(23, 59)
        )
        basis = "ORS 90.160(1)"
    else:
        if special_hour_start:
            # ORS 90.160(2)(b): clock starts at 11:59 PM the day both service methods
            # completed, regardless of the actual time of day service happened.
            clock_start = datetime.combine(service_date, time(23, 59))
            basis = "ORS 90.160(2)(b)"
        else:
            if service_time is None:
                return (
                    "MISSING INPUT, NO DEADLINE COMPUTED: service_time is required for "
                    "an hour-based notice period unless it terminates the tenancy and "
                    "was served by mail_and_attach or email_and_mail. Ask the tenant "
                    "what time the notice was served, then call this tool again."
                )
            # ORS 90.160(2)(a): clock starts immediately upon service.
            clock_start = datetime.combine(service_date, service_time)
            basis = "ORS 90.160(2)(a)"
        deadline = clock_start + timedelta(hours=period_value)
        if mail_extension_applies:
            # ORS 90.155(2)'s three-day extension applies on top of the hour count.
            deadline += timedelta(days=3)
    # Applies to both branches: ORS 90.155(2)'s mail extension is available whether
    # the underlying period is day-based or hour-based, whenever service was by
    # first-class mail alone.
    basis += " and ORS 90.155(2)" if mail_extension_applies else ""

    caveats = []
    if service_method == NoticeServiceMethod.MAIL_AND_ATTACH:
        caveats.append(
            "mail-and-attach service is only valid if the written rental agreement authorizes it (ORS 90.155(1)(c))"
        )
    if service_method in (
        NoticeServiceMethod.EMAIL_AND_MAIL,
        NoticeServiceMethod.EMAIL_ONLY,
    ):
        caveats.append(
            "e-mail service is only valid if a signed ORS 90.155(1)(d) addendum authorizes it"
        )

    other_unit = "days" if period_unit == "hours" else "hours"
    lines = [
        "NOTICE DEADLINE CALCULATION — relay this result as given; do not recompute it by hand.",
        "",
        f"Inputs: {period_value} {period_unit}, served {service_date.isoformat()}"
        + (
            f" at {service_time.strftime('%H:%M')}"
            if service_time and period_unit == "hours" and not special_hour_start
            else ""
        )
        + f", method={service_method.value}, termination notice={is_termination_notice}.",
        "",
        f"UNIT CHECK: this is a {period_value}-{period_unit[:-1]} period. It is "
        f"{period_value} {period_unit.upper()}, NOT {period_value} {other_unit.upper()} "
        f'— never restate it using the word "{other_unit}".',
        "",
        f"Legal basis: {basis}."
        + (
            " The ORS 90.155(2) mail extension adds 3 days because the notice was mailed alone."
            if mail_extension_applies
            else ""
        ),
    ]
    if caveats:
        lines.append("Caveat: " + "; ".join(caveats) + ".")
    lines += [
        "",
        f"DEADLINE: {deadline.strftime('%A, %B %d, %Y at %I:%M %p')}. Do NOT push this to "
        "the next business day — ORS 90.160 overrides ORCP 10, so weekends and holidays "
        "do not extend it. Relay this exact date/time.",
    ]
    return "\n".join(lines)


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
