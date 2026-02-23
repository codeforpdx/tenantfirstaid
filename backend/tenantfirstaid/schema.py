from typing import Final, Literal

from pydantic import BaseModel, Field

LETTER_START: Final = "-----generate letter-----"
LETTER_END: Final = "-----end of letter-----"


class TextChunk(BaseModel):
    type: Literal["text"] = "text"
    text: str = Field(description="The message text")


class ReasoningChunk(BaseModel):
    type: Literal["reasoning"] = "reasoning"
    reasoning: str = Field(description="The model reasoning")


class LetterChunk(BaseModel):
    type: Literal["letter"] = "letter"
    letter: str = Field(description="The letter content")


ResponseChunk = TextChunk | ReasoningChunk | LetterChunk
