"""Models exported to the frontend as TypeScript types.

Used by pydantic2ts via `make generate-types`. All BaseModel subclasses
visible in this module's namespace are included in the generated output.
"""

from pydantic import RootModel

from tenantfirstaid.location import Location  # noqa: F401
from tenantfirstaid.schema import LetterChunk, ReasoningChunk, TextChunk


class ResponseChunk(RootModel[TextChunk | ReasoningChunk | LetterChunk]):
    """Union of all possible streaming response chunk types."""
