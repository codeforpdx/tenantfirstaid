"""Structured legal-aid referral catalog.

Single source of truth for the referrals bundled into the frontend Referrals
page and looked up by the agent's get_legal_aid_referrals tool. Backed by
referrals_data.json and validated at import time.
"""

import json
from enum import StrEnum
from pathlib import Path
from typing import Final, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .location import OregonCity, UsaState

_TIME_PATTERN: Final = r"^([01]\d|2[0-3]):[0-5]\d$"

# IDs that must be present in referrals_data.json because other modules
# (e.g. constants.py's OREGON_LAW_CENTER_PHONE_NUMBER) look them up directly.
_REQUIRED_IDS: Final = {"laso"}


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
    model_config = ConfigDict(extra="forbid", frozen=True)

    days: list[Weekday]
    start: str = Field(
        pattern=_TIME_PATTERN, description="24-hour start time, e.g. '09:00'."
    )
    end: str = Field(
        pattern=_TIME_PATTERN, description="24-hour end time, e.g. '17:00'."
    )

    @model_validator(mode="after")
    def _end_after_start(self) -> "HoursBlock":
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) must be after start ({self.start})")
        return self


class GeographicScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: UsaState = UsaState.OREGON
    cities: list[OregonCity] = Field(
        default_factory=list,
        description="Cities served. Empty means the entire state is served.",
    )


class Referral(BaseModel):
    """A single legal-aid or tenant-services referral."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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

    missing = _REQUIRED_IDS - set(ids)
    if missing:
        raise ValueError(
            f"referrals_data.json is missing required id(s): {sorted(missing)}"
        )


def _load_referrals() -> list[Referral]:
    raw = json.loads(_REFERRALS_DATA_PATH.read_text())
    referrals = [Referral.model_validate(entry) for entry in raw]
    _validate_referrals(referrals)
    return referrals


REFERRALS: Final[list[Referral]] = _load_referrals()
REFERRALS_BY_ID: Final[dict[str, Referral]] = {r.id: r for r in REFERRALS}
