"""
Module for Flask Chat View
"""

import logging
import re
from typing import Any, Generator

from flask import Response, current_app, request, stream_with_context
from flask.views import View
from langchain_core.messages import (
    AnyMessage,
    ContentBlock,
)

from .langchain_chat_manager import LangChainChatManager
from .location import OregonCity, UsaState
from .schema import (
    LETTER_END,
    LETTER_START,
    LetterChunk,
    ReasoningChunk,
    ResponseChunk,
    TextChunk,
)

LETTER_START_REGEX = re.compile(re.escape(LETTER_START), re.IGNORECASE)
LETTER_END_REGEX = re.compile(re.escape(LETTER_END), re.IGNORECASE)

_logger = logging.getLogger(__name__)


def _classify_blocks(
    stream: Generator[ContentBlock, Any, None],
) -> Generator[ResponseChunk, Any, None]:
    """
    Convert raw LangChain content blocks into typed ResponseChunk objects.

    Watches for letter delimiters inside text blocks and emits a
    LetterChunk if it exists.
    """
    in_letter = False
    letter_parts: list[str] = []

    for content_block in stream:
        match content_block["type"]:
            case "reasoning":
                yield ReasoningChunk(reasoning=content_block["reasoning"])

            case "text":
                text = content_block["text"]

                if in_letter:
                    # Look for the end stop.
                    end_match = LETTER_END_REGEX.search(text)
                    if end_match:
                        letter_parts.append(text[: end_match.start()])
                        # Finalize the letter
                        yield LetterChunk(letter="".join(letter_parts).strip())
                        in_letter = False
                    else:
                        letter_parts.append(text)

                else:
                    # Look for the start of the letter
                    start_match = LETTER_START_REGEX.search(text)
                    if start_match:
                        before = text[: start_match.start()].strip()
                        if before:
                            yield TextChunk(text=before)
                        rest = text[start_match.end() :]
                        end_match = LETTER_END_REGEX.search(rest)
                        if end_match:
                            yield LetterChunk(letter=rest[: end_match.start()].strip())
                        else:
                            in_letter = True
                            letter_parts = [rest]
                    else:
                        yield TextChunk(text=text)

    if in_letter and letter_parts:
        _logger.warning(
            "Stream ended while inside letter block; yielding partial letter."
        )
        yield LetterChunk(letter="".join(letter_parts).strip())


class ChatView(View):
    def __init__(self) -> None:
        self.chat_manager = LangChainChatManager()

    def dispatch_request(self, *args, **kwargs) -> Response:
        """
        Handle client POST request
        Expects JSON body with:
        - messages: List of AnyMessage dicts
        - city: Optional city name
        - state: State abbreviation
        """

        data: dict[str, Any] = request.json

        messages: list[AnyMessage] = data["messages"]
        city: OregonCity | None = OregonCity.from_maybe_str(data["city"])
        state: UsaState = UsaState.from_maybe_str(data["state"])

        # Create a stable & unique thread ID based on client IP and endpoint
        # TODO: consider using randomly-generated token stored client-side in
        #       a secure-cookie
        tid: str | None = None

        def generate() -> Generator[str, Any, None]:
            response_stream: Generator[ContentBlock] = (
                self.chat_manager.generate_streaming_response(
                    messages=messages,
                    city=city,
                    state=state,
                    thread_id=tid,
                )
            )
            for content_block in _classify_blocks(response_stream):
                current_app.logger.debug(f"Received content_block: {content_block}")
                yield content_block.model_dump_json() + "\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
