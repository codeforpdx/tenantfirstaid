"""
This module defines Tools for an Agent to call
"""

import json
import logging
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Callable, Final, Literal, Optional, Type, cast

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
    framework for landlord/tenant notices. ORS 90.155(1) itself carves out ORS 90.300
    (security deposit accountings), 90.315 (utility/service charges), 90.425
    (abandoned personal property), and 90.675 (manufactured dwelling abandonment) —
    those notice types supply their own delivery rule and are NOT modeled here. It
    also does not model ORS 90.150(3) (when a mailed notice counts as "served" for
    actual-notice-equivalence purposes).
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
    """For a termination notice, ORS 90.155(5): first-class mail AND e-mail, required,
    valid only under a signed ORS 90.155(1)(d) addendum. No 90.155(2) extension —
    instead gets the ORS 90.160(2)(b) 11:59 PM clock start. For a non-termination
    notice, this is ordinary ORS 90.155(1)(b) mail service with the e-mail copy as an
    ORS 90.155(3) alternative method alongside it: the 90.155(2) three-day extension
    applies and there is no special clock start."""

    EMAIL_ONLY = "email_only"
    """ORS 90.155(1)(d): e-mail alone. Valid only under a signed addendum, and only for a
    notice that does NOT terminate the tenancy — e-mail alone never validly serves a
    termination notice (ORS 90.155(5))."""


def _labeled_block(label: str, items: list[str]) -> list[str]:
    """Render `items` one per line under `label`, or nothing when empty.

    Joining these with "; " is not safe: an entry may contain a semicolon of its
    own, which leaves a reader unable to tell an entry boundary from punctuation
    inside an entry. One entry per line makes the boundaries unambiguous no
    matter how many entries there are or what punctuation they hold.
    """
    if not items:
        return []
    heading = f"{label}s:" if len(items) > 1 else f"{label}:"
    return [heading] + [f"  - {item}." for item in items]


class NoticeDeadlineInputSchema(BaseModel):
    """Input schema for the calculate_ors_90_160_notice_deadline tool."""

    # These bounds close the same overflow hole period_value's le=1000 closes,
    # from the other operand: date(9999, 12, 31) plus any period overflows the
    # date arithmetic in the tool body. date(1973, 1, 1) predates the Oregon
    # Residential Landlord and Tenant Act, so no real notice can fall below it.
    # date(2100, 1, 1) is far past any plausible service date and still leaves
    # headroom above it for the longest accepted period (1000 days) plus the
    # three-day mail extension. A Pydantic bound rather than an in-body check
    # for the same reason period_value's are: a ValidationError on tool args
    # comes back to the model as a correctable ToolMessage, whereas an
    # OverflowError raised inside the tool body escapes the graph.
    service_date: date = Field(
        ge=date(1973, 1, 1),
        le=date(2100, 1, 1),
        description="""The date the notice was served. For mail_and_attach or
        email_and_mail, this is the date BOTH methods were completed.""",
    )
    service_time: Optional[time] = Field(
        default=None,
        description="""Clock time the notice was served, 24-hour or 12-hour form (e.g.
        "14:30" or "2:30 PM"). Required when period_unit is "hours", UNLESS
        is_termination_notice is true and service_method is mail_and_attach or
        email_and_mail — those start the clock at 11:59 PM regardless of what time
        service actually happened.""",
    )
    # le=1000 sits above the longest real ORS 90 period (365 days for a park
    # closure, 72 hours for the shortest termination notices) yet below any
    # date-shaped value. Without it, 20260101 raises OverflowError in the days
    # branch and, worse, silently returns a fully formatted tenant-facing
    # deadline in the year 4337 in the hours branch — so the bound must be
    # tight, not merely below the overflow threshold. A Pydantic bound rather
    # than an in-body guard because LangGraph wraps a ValidationError on tool
    # args as a ToolInvocationError and hands it back to the model as a readable
    # ToolMessage it can correct, while anything raised inside the tool body
    # escapes the graph.
    period_value: int = Field(
        gt=0,
        le=1000,
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
        email_and_mail — mail AND e-mail. For a termination notice this is REQUIRED
        (not optional) under ORS 90.155(5), valid only under a signed addendum; same
        11:59 PM clock start as mail_and_attach, no 90.155(2) extension. For a
        non-termination notice, this is ordinary first-class mail service under
        90.155(1)(b) with the e-mail copy as an ORS 90.155(3) alternative method —
        the 90.155(2) three-day extension applies, same as first_class_mail alone.
        email_only — e-mail alone, valid only under a signed addendum and ONLY for a
        notice that does not terminate the tenancy — e-mail alone never validly
        serves a termination notice.""",
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


_AGENT_NOTES_FENCE: Final = (
    "=== AGENT NOTES — accuracy-checking scaffolding, NEVER relay this "
    "section to the tenant ==="
)
_RELAY_MARKER: Final = (
    "--- relay everything below this line to the tenant, verbatim; "
    "do not recompute it ---"
)
# A blank list entry renders as a blank output line once joined with "\n" —
# named so it reads as a deliberate spacer, not a stray empty string.
_BLANK_LINE: Final = ""


def _agent_notes_relay(agent_notes: list[str], tenant_lines: list[str]) -> str:
    """Join agent-only scaffolding and a tenant-facing answer behind the
    shared AGENT NOTES fence and relay marker, so every return path uses one
    literal copy of both instead of a drift-prone duplicate.
    """
    return "\n".join(
        [
            _AGENT_NOTES_FENCE,
            _BLANK_LINE,
            *agent_notes,
            _BLANK_LINE,
            _RELAY_MARKER,
            *tenant_lines,
        ]
    )


def _missing_service_time_refusal(
    *,
    mailing_occurred: bool,
    is_termination_notice: bool,
    mail_extension_applies: bool,
) -> str:
    """Refusal text for an hour-based period served with no service_time.

    The message is an unconditional stem plus three clauses that gate on three
    different conditions, so it is composed rather than branched. The stem is
    true on every path that reaches here. The mailing clause needs only that a
    mailing occurred. The next-step clause cites ORS 90.396(1), 90.398(1),
    90.403(1) and 90.445(1), all of which are termination statutes, so it gates
    on is_termination_notice. The extension clause gates on
    mail_extension_applies, which is narrower than mailing_occurred because ORS
    90.155(2) reaches only subsection (1)(b) service.
    """
    parts = [
        "MISSING INPUT, NO DEADLINE COMPUTED: an hour-based period served this "
        "way starts running at the moment of service under ORS 90.160(2)(a)"
    ]
    if mailing_occurred:
        # Deliberately method-neutral: this branch is also reached by
        # mail_and_attach (ORS 90.155(1)(c)) and email_and_mail, so naming
        # first class mail here would miscite the method actually used.
        parts.append(
            ", which for service by mail is the moment the landlord mailed the "
            "notice, not the moment the tenant received it"
        )
    parts.append(
        ". Do NOT guess that time and do NOT substitute the delivery time. Instead, "
    )
    if is_termination_notice:
        parts.append(
            "ask the tenant what termination date and time the notice itself "
            "states: ORS 90.396(1), 90.398(1), 90.403(1) and 90.445(1) each "
            "require the notice to state them."
        )
    else:
        parts.append(
            "ask the tenant for the exact date and time the notice was served."
        )
    if mail_extension_applies:
        parts.append(
            " ORS 90.155(2) also requires the landlord to have already included "
            "the three-day mail extension in the period the notice provides."
        )
    parts.append(
        " If the tenant can supply the exact time of service, call this tool "
        "again with service_time set."
    )
    tenant_facing = (
        "I need a bit more detail before I can calculate an exact "
        "deadline for this notice — let me follow up on that."
    )
    return _agent_notes_relay(
        agent_notes=["".join(parts)],
        tenant_lines=[_BLANK_LINE, tenant_facing],
    )


@tool(args_schema=NoticeDeadlineInputSchema, response_format="content")
def calculate_ors_90_160_notice_deadline(
    service_date: date,
    period_value: int,
    period_unit: Literal["hours", "days"],
    service_method: NoticeServiceMethod,
    is_termination_notice: bool,
    service_time: Optional[time] = None,
) -> str:
    """Compute the exact deadline of an Oregon landlord-tenant notice period.

    Call this instead of doing the date/time math by hand — ORS 90.160's hour-vs-day
    counting rules, the ORS 90.155(2) mail extension, and the ORS 90.155(1)(c)/(5)
    mail-and-attach/e-mail-and-mail clock start are easy to mix up, and mixing up hours
    with days produces a deadline that's off by roughly a factor of 24.

    Do not call this for a notice governed by ORS 90.300, 90.315, 90.425, or 90.675 —
    those statutes supply their own service/timing rule instead of ORS 90.155/90.160.

    Args:
        service_date: Date the notice was served (or, for mail_and_attach/email_and_mail,
            the date both methods were completed).
        period_value: The notice period's length, in period_unit's unit.
        period_unit: "hours" or "days" — must match the governing statute exactly.
        service_method: How the notice was served, under ORS 90.155(1) or (5).
        is_termination_notice: True if the notice terminates the tenancy.
        service_time: Clock time of service. Required for hour-based periods unless the
            ORS 90.160(2)(b) special start applies (see is_termination_notice).

    Returns:
        A formatted result with a single section header, the AGENT NOTES fence:
        everything from the fence down to and including the relay marker is
        accuracy-checking scaffolding for you, never relay it; everything after
        the marker is the tenant-facing answer, which you relay to the tenant
        as given, don't recompute it.
    """
    if service_method == NoticeServiceMethod.EMAIL_ONLY and is_termination_notice:
        tenant_facing = (
            "SERVICE INVALID: this notice was served by e-mail only. Under "
            "ORS 90.155(5), e-mail alone cannot validly serve a notice "
            "ending your tenancy, so no deadline applies to it as served."
        )
        return _agent_notes_relay(
            agent_notes=[
                "SERVICE INVALID, NO DEADLINE COMPUTED: e-mail alone can never "
                "validly serve a notice terminating the tenancy — ORS 90.155(5) "
                "requires BOTH first-class mail AND e-mail for a termination "
                "notice sent by e-mail. Do not compute or state a deadline for "
                "it. If the notice was also sent by first-class mail, call this "
                "tool again with service_method=email_and_mail.",
            ],
            tenant_lines=[_BLANK_LINE, tenant_facing],
        )
    # email_and_mail + non-termination isn't ORS 90.155(5) (that's termination-only) —
    # it's ordinary ORS 90.155(1)(b) mail service with the e-mail copy as an ORS
    # 90.155(3) alternative method alongside it. Treat it exactly like
    # first_class_mail: the 90.155(2) extension applies, no special clock start.
    email_and_mail_as_mail_alternative = (
        service_method == NoticeServiceMethod.EMAIL_AND_MAIL
        and not is_termination_notice
    )
    # A mailing having happened is NOT the same condition as the extension
    # applying, which is why these are two variables rather than one. ORS
    # 90.155(1) makes first class mail (1)(b) and mail-and-attach (1)(c)
    # separate methods, and 90.155(2) reaches only "a notice ... served by mail
    # under subsection (1)(b)".
    mailing_occurred = service_method in (
        NoticeServiceMethod.FIRST_CLASS_MAIL,
        NoticeServiceMethod.MAIL_AND_ATTACH,
        NoticeServiceMethod.EMAIL_AND_MAIL,
    )
    # ORS 90.155(2) grants the three-day extension only "If a notice is served by
    # mail under subsection (1)(b) of this section" — first class mail
    # specifically. first_class_mail is (1)(b), so it qualifies. mail_and_attach
    # is the distinct method of subsection (1)(c), so it is excluded even though
    # a mailing occurred. email_and_mail on a non-termination notice is included
    # for the opposite reason: its mail leg IS (1)(b) service, and ORS 90.155(3)
    # permits the e-mail copy alongside it — a party "may utilize alternative
    # methods of notifying the other so long as the alternative method is in
    # addition to one of the service methods described in subsection (1)."
    mail_extension_applies = (
        service_method == NoticeServiceMethod.FIRST_CLASS_MAIL
        or email_and_mail_as_mail_alternative
    )
    # ORS 90.160(2) is not termination-only: it opens "For references in this
    # chapter to periods or notices based on a number of hours", which is
    # chapter-wide, so citing (2)(a) for an ordinary hour-based period is right.
    # The termination limit sits inside paragraph (b), which begins "For notices
    # to terminate a tenancy" before naming the 90.155(1)(c) mailed-and-attached
    # case and the 90.155(5) mailed-and-e-mailed case — so gating (2)(b) on
    # is_termination_notice as well as service_method is right too.
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
            # The non-termination hour-based case that flows through here appears
            # unreachable in practice: no ORS 90 written notice served under
            # 90.155 is both hour-based and non-terminating. 90.322(1)(f)'s
            # 24-hour entry notice is "actual notice" under the separate ORS
            # 90.150 service statute, and 90.365(2)'s 48-hour essential-services
            # notice conditionally terminates. The branch stays because
            # 90.160(2)(a) is written as the general rule, but the coverage hole
            # is documented rather than silent.
            if service_time is None:
                return _missing_service_time_refusal(
                    mailing_occurred=mailing_occurred,
                    is_termination_notice=is_termination_notice,
                    mail_extension_applies=mail_extension_applies,
                )
            # ORS 90.160(2)(a): clock starts immediately upon service.
            clock_start = datetime.combine(service_date, service_time)
            basis = "ORS 90.160(2)(a)"
        # Wall-clock arithmetic, not elapsed time — e.g. a 72-hour notice served the
        # Friday before spring-forward lands an hour "early" read as elapsed time.
        # This is a defensible reading of ORS 90.160(2)'s "consecutive hours" and is a
        # deliberate choice, not an oversight.
        deadline = clock_start + timedelta(hours=period_value)
        if mail_extension_applies:
            # ORS 90.155(2)'s three-day extension applies on top of the hour count.
            deadline += timedelta(days=3)
    # Applies to both branches: ORS 90.155(2)'s mail extension is available whether
    # the underlying period is day-based or hour-based, whenever service included
    # first-class mail under ORS 90.155(1)(b) (alone, or alongside e-mail for a
    # non-termination notice).
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
    # Deliberately not a caveat. The other two entries are conditions on whether
    # service was valid at all ("only valid if ..."), while this one explains why
    # the e-mail copy leaves the deadline alone. Under a shared "Caveat:" label a
    # reader carries the "only valid if" framing into this sentence and concludes
    # the e-mail copy is what carried the notice, which is backwards.
    notes = []
    if email_and_mail_as_mail_alternative:
        # This hedge is in the returned output rather than only in source
        # comments because of the failure direction. If the reading that the
        # mail leg is the operative service is wrong, the tenant is told their
        # deadline is three days later than it really is and may act after it
        # has already passed.
        notes.append(
            "this notice was served by first-class mail under ORS 90.155(1)(b); the "
            "e-mail copy is an ORS 90.155(3) alternative method that neither adds "
            "nor removes time from the deadline. That reading rests on treating "
            "the mail leg as the operative service. Whether a signed ORS "
            "90.155(1)(d) e-mail addendum instead makes the e-mail leg "
            "independently sufficient — which would mean no three-day extension "
            "is owed — is not settled. If you are relying on the last three days "
            "of this deadline, confirm it with a lawyer or legal aid before acting"
        )

    other_unit = "days" if period_unit == "hours" else "hours"
    # The relay marker sits on the scaffolding side of the boundary: the old
    # "=== TENANT-FACING ANSWER ===" header lived inside the tenant-facing
    # region, so a model relaying that region verbatim would have leaked the
    # agent-directed instruction into the tenant's chat.
    agent_notes = [
        _AGENT_NOTES_FENCE,
        f"Inputs: {period_value} {period_unit}, served {service_date.isoformat()}"
        + (
            f" at {service_time.strftime('%H:%M')}"
            if service_time and period_unit == "hours" and not special_hour_start
            else ""
        )
        + f", method={service_method.value}, termination notice={is_termination_notice}.",
        f"UNIT CHECK: this is a {period_value}-{period_unit[:-1]} period. It is "
        f"{period_value} {period_unit.upper()}, NOT {period_value} {other_unit.upper()} "
        f'— never restate it using the word "{other_unit}".',
        _RELAY_MARKER,
    ]

    tenant_lines = [
        _BLANK_LINE,
        f"Legal basis: {basis}."
        + (
            " The ORS 90.155(2) mail extension adds 3 days because the notice was served by first-class mail."
            if mail_extension_applies
            else ""
        ),
    ]
    tenant_lines += _labeled_block("Caveat", caveats)
    tenant_lines += _labeled_block("Note", notes)
    tenant_lines += [
        _BLANK_LINE,
        f"DEADLINE: {deadline.strftime('%A, %B %d, %Y at %I:%M %p')}. This deadline is "
        "NOT extended for weekends or holidays — ORS 90.160 overrides ORCP 10.",
    ]
    return "\n".join(agent_notes + tenant_lines)


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
