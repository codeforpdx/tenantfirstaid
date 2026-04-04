from typing import Literal

from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    type: Literal["text"] = "text"
    content: str = Field(description="The message text")


class ReasoningChunk(BaseModel):
    type: Literal["reasoning"] = "reasoning"
    content: str = Field(description="The model reasoning")


class LetterChunk(BaseModel):
    type: Literal["letter"] = "letter"
    content: str = Field(description="The letter content")


class EndOfStreamChunk(BaseModel):
    type: Literal["end_of_stream"] = "end_of_stream"


ResponseChunk = TextChunk | ReasoningChunk | LetterChunk | EndOfStreamChunk
