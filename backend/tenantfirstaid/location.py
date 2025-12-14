"""
This module defines city/state types with methods to sanitize
and normalize inputs to enumerated values
"""

from enum import StrEnum
from typing import Optional

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


class OregonCity(StrEnum):
    PORTLAND = "portland"
    EUGENE = "eugene"

# class OregonCity:
#     value: Optional[_InnerOregonCity]

#     def __init__(self, v: Optional[str]):
#         try:
#             if v is None:
#                 self.value = None
#             else:
#                 self.value = _InnerOregonCity(city_or_state_input_sanitizer(v))
#         except ValueError:
#             self.value = None
#         except Exception as e:
#             raise e
#         super().__init__()

#     def __repr__(self) -> str:
#         return str(self.value) if self.value is not None else "null"

#     def else_empty(self) -> str:
#         return str(self.value) if self.value is not None else ""

#     def lower(self) -> str:
#         return self.else_empty().lower()

#     def upper(self) -> str:
#         return self.else_empty().upper()


class UsaState(StrEnum):
    """
    Enumeration that represents names in the set of States in the United States of America
    """
    OREGON = "or"
    OTHER = "other"

    # def __repr__(self) -> str:
    #     return str(self.value) if self.value is not None else "null"

    # def else_empty(self) -> str:
    #     return str(self.value) if self.value is not None else ""

    # def lower(self) -> str:
    #     return self.else_empty().lower()

    # def upper(self) -> str:
    #     return self.else_empty().upper()


class TFAAgentStateSchema(AgentState):
    state: UsaState
    city: Optional[OregonCity]
