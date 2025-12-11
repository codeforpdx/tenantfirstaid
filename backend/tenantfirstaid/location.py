"""
This module defines city/state types with methods to sanitize
and normalize inputs to enumerated values
"""

from enum import StrEnum
from typing import Any, Dict, List, Optional

from langchain.agents import AgentState
from pydantic import BaseModel


def city_or_state_input_sanitizer(location: Optional[str], max_len: int = 9) -> str:
    """Validate and sanitize city or state input."""
    if location is None or not isinstance(location, str):
        return ""
    if not location.isalpha():
        raise ValueError(f"Invalid city or state input: {location}")
    if len(location) < 2 or len(location) > max_len:
        raise ValueError(f"Invalid city or state input length: {location}")
    return location.lower()


class _InnerOregonCity(StrEnum):
    PORTLAND = "portland"
    EUGENE = "eugene"


class OregonCity(BaseModel, arbitrary_types_allowed=True):
    value: Optional[_InnerOregonCity] = None

    @classmethod
    def from_str(cls, v: Optional[str]) -> "OregonCity":
        instance = cls()
        if v is None:
            instance.value = None
        else:
            try:
                instance.value = _InnerOregonCity(v.lower())
            except ValueError:
                instance.value = None
        return instance

    # def __init__(self, v: str):
    #     try:
    #         if v is None:
    #             self.value = None
    #         else:
    #             self.value = _InnerOregonCity(v.lower())
    #     except ValueError:
    #         self.value = None
    #     except Exception as e:
    #         raise e
    #     super().__init__()

    def __repr__(self) -> str:
        return str(self.value) if self.value is not None else "null"

    def else_empty(self) -> str:
        return str(self.value) if self.value is not None else ""

    def lower(self) -> str:
        return self.else_empty().lower()

    def upper(self) -> str:
        return self.else_empty().upper()


class _InnerUsaState(StrEnum):
    OREGON = "or"
    OTHER = "OTHER"


class UsaState(BaseModel, arbitrary_types_allowed=True):
    value: Optional[_InnerUsaState] = None

    # def __init__(self, v: str):
    #     try:
    #         if v is None:
    #             self.value = None
    #         else:
    #             self.value = _InnerUsaState(v.lower())
    #     except ValueError:
    #         self.value = None
    #     except Exception as e:
    #         raise e
    #     super().__init__()

    @classmethod
    def from_str(cls, v: Optional[str]) -> "UsaState":
        instance = cls()
        if v is None:
            instance.value = None
        else:
            try:
                instance.value = _InnerUsaState(v.lower())
            except ValueError:
                instance.value = None
        return instance

    def __repr__(self) -> str:
        return str(self.value) if self.value is not None else "null"

    def else_empty(self) -> str:
        return str(self.value) if self.value is not None else ""

    def lower(self) -> str:
        return self.else_empty().lower()

    def upper(self) -> str:
        return self.else_empty().upper()


class TFAAgentStateSchema(AgentState):
    state: str
    city: Optional[str]
