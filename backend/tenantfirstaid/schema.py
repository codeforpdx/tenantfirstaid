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


ResponseChunk = TextChunk | ReasoningChunk | LetterChunk
