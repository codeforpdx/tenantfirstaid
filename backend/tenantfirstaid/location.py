"""Location types and validation for user city and state.

Provides :class:`OregonCity` and :class:`UsaState` enums with safe parsing methods
that handle frontend input, plus a state schema for LangGraph agent operations.
"""

from enum import StrEnum
from typing import NotRequired, Optional

from langchain.agents import AgentState
from pydantic import BaseModel


def city_or_state_input_sanitizer(location: Optional[str], max_len: int = 9) -> str:
    """Validate and sanitize city or state input.

    Args:
        location: City or state name to validate.
        max_len: Maximum allowed string length (default 9).

    Returns:
        Lowercase validated location string, or empty string if input is None.

    Raises:
        ValueError: If input contains non-alphabetic characters, invalid length, or whitespace.
    """
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
    """Oregon cities with jurisdiction-specific housing codes in the corpus."""

    PORTLAND = "portland"
    """Portland, Oregon, the largest city in the state and a major hub for housing code enforcement."""

    EUGENE = "eugene"
    """Eugene, Oregon, a city known for its progressive housing policies and code enforcement."""

    @classmethod
    def from_maybe_str(cls, c: Optional[str] = None) -> Optional["OregonCity"]:
        """Parse a city string to an OregonCity enum value.

        Args:
            c: City name string, or None.

        Returns:
            [`OregonCity`](`~location.OregonCity`) enum value if recognized, or None if not recognized or input is None.
        """
        if c is None:
            return None
        else:
            city: Optional[OregonCity]
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
    """Oregon, a state in the Pacific Northwest region of the United States."""

    OTHER = "other"
    """Any state other than Oregon, or an unrecognized state input."""

    @classmethod
    def from_maybe_str(cls, s: Optional[str] = None) -> "UsaState":
        """Parse a state string to a UsaState enum value.

        Args:
            s: State abbreviation or name, or None.

        Returns:
            [`UsaState.OREGON`](`~location.UsaState`) if "or" is recognized, otherwise [`UsaState.OTHER`](`~location.UsaState`).
        """
        if s is None:
            return cls.OTHER
        else:
            match s.strip().upper():
                case "OR":
                    state = cls.OREGON
                case _:
                    state = cls.OTHER
            return state


class Location(BaseModel):
    """City and state as sent by the frontend.

    `state=None` is treated as :class:`UsaState`.OTHER by the backend.
    """

    city: OregonCity | None = None
    """User's city, if in Oregon and recognized by the backend."""

    state: UsaState | None = None
    """User's state, if recognized by the backend. None is treated as :class:`UsaState`.OTHER."""


class TFAAgentStateSchema(AgentState):
    """State schema for the Tenant First Aid agent graph.

    Includes user location (state and optional city) that flows through the agent
    to inform RAG retrieval and system prompt generation. The NotRequired annotation
    makes the city field optional in LangSmith Studio's input panel.
    """

    state: UsaState
    """User's state."""
    city: NotRequired[Optional[OregonCity]]
    """User's city, optional."""
