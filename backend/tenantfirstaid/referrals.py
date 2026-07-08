"""Structured legal-aid referral catalog.

Single source of truth for the referrals shown on the frontend Referrals page
(served via GET /api/referrals) and looked up by the agent's
get_legal_aid_referrals tool. Backed by referrals_data.json and validated at
import time.
"""

import json
from enum import StrEnum
from pathlib import Path
from typing import Final, Optional

from pydantic import BaseModel, Field

from .location import OregonCity, UsaState


class ServiceType(StrEnum):
    LEGAL_REPRESENTATION = "legal_representation"
    ANSWER_QUESTIONS = "answer_questions"


class ProviderType(StrEnum):
    ATTORNEY = "attorney"
    LICENSED_PARALEGAL = "licensed_paralegal"
    NON_ATTORNEY = "non_attorney"


class CaseStage(StrEnum):
    BEFORE_COURT = "before_court"
    IN_COURT = "in_court"


class Weekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class HoursBlock(BaseModel):
    days: list[Weekday]
    start: str = Field(description="24-hour start time, e.g. '09:00'.")
    end: str = Field(description="24-hour end time, e.g. '17:00'.")


class GeographicScope(BaseModel):
    state: UsaState = UsaState.OREGON
    cities: list[OregonCity] = Field(
        default_factory=list,
        description="Cities served. Empty means the entire state is served.",
    )


class Referral(BaseModel):
    """A single legal-aid or tenant-services referral."""

    id: str
    organization: str
    service_types: list[ServiceType]
    provider_types: list[ProviderType] = Field(default_factory=list)
    geographic_scope: GeographicScope
    eligibility: list[str] = Field(
        default_factory=list, description="Prerequisites a tenant must meet."
    )
    case_stages: list[CaseStage] = Field(default_factory=list)
    hours: list[HoursBlock] = Field(default_factory=list)
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = Field(
        default=None,
        description="Free-text markdown for instructions not captured by other fields.",
    )


_REFERRALS_DATA_PATH: Final = Path(__file__).parent / "referrals_data.json"


def _validate_referrals(referrals: list[Referral]) -> None:
    ids = [r.id for r in referrals]
    if len(ids) != len(set(ids)):
        raise ValueError("Referral IDs must be unique.")

def _load_referrals() -> list[Referral]:
    raw = json.loads(_REFERRALS_DATA_PATH.read_text())
    referrals = [Referral.model_validate(entry) for entry in raw]
    _validate_referrals(referrals)
    return referrals


REFERRALS: Final[list[Referral]] = _load_referrals()
REFERRALS_BY_ID: Final[dict[str, Referral]] = {r.id: r for r in REFERRALS}
