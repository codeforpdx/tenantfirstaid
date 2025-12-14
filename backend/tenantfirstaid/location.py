"""
This module defines city/state types with methods to sanitize
and normalize inputs to enumerated values
"""

from enum import StrEnum
from typing import Optional

from langchain.agents import AgentState


def city_or_state_input_sanitizer(location: Optional[str], max_len: int = 9) -> str:
    """Validate and sanitize city or state input."""
    if location is None or not isinstance(location, str):
        return ""
    if not location.isalpha():
        raise ValueError(f"Invalid city or state input characters: '{location}'")
    if len(location) < 2 or len(location) > max_len:
        raise ValueError(f"Invalid city or state input length: '{location}'")
    if location.strip() != location:
        raise ValueError(f"Invalid whitespace around city or state input: '{location}'")
    return location.lower()


class OregonCity(StrEnum):
    PORTLAND = "portland"
    EUGENE = "eugene"

    @classmethod
    def from_maybe_str(cls, c: Optional[str] = None) -> Optional["OregonCity"]:
        if c is None:
            return None
        else:
            match c.strip().lower():
                case "eugene":
                    city = cls.EUGENE
                case "portland":
                    city = cls.PORTLAND
                case _:
                    city = None
            return city


class UsaState(StrEnum):
    """
    Enumeration that represents names in the set of States in the United States of America
    """

    OREGON = "or"
    OTHER = "other"

    @classmethod
    def from_maybe_str(cls, s: Optional[str] = None) -> "UsaState":
        if s is None:
            return cls.OTHER
        else:
            match s.strip().upper():
                case "OR":
                    state = cls.OREGON
                case _:
                    state = cls.OTHER
            return state


class TFAAgentStateSchema(AgentState):
    state: UsaState
    city: Optional[OregonCity]
