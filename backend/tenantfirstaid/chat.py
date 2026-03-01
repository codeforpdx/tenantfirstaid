"""
Module for Flask Chat View
"""

from typing import Any, Dict, Generator, List

from flask import Response, current_app, request, stream_with_context
from flask.views import View
from langchain_core.messages import ContentBlock

from .langchain_chat_manager import LangChainChatManager
from .location import OregonCity, UsaState
from .schema import (
    LetterChunk,
    ReasoningChunk,
    ResponseChunk,
    TextChunk,
)


def _classify_blocks(
    stream: Generator[ContentBlock, Any, None],
) -> Generator[ResponseChunk, Any, None]:
    """Convert raw LangChain content blocks into typed ResponseChunk objects."""
    for content_block in stream:
        match content_block["type"]:
            case "reasoning":
                yield ReasoningChunk(content=content_block["reasoning"])
            case "text":
                yield TextChunk(content=content_block["text"])
            case "letter":
                yield LetterChunk(content=content_block["content"])
            case _:
                current_app.logger.warning(
                    f"Unhandled block type: {content_block['type']}"
                )


class ChatView(View):
    def __init__(self) -> None:
        self.chat_manager = LangChainChatManager()

    def dispatch_request(self, *args, **kwargs) -> Response:
        """
        Handle client POST request
        Expects JSON body with:
        - messages: List of message dicts from the frontend ({"role": ..., "content": ..., "id": ...})
        - city: Optional city name
        - state: State abbreviation
        """

        data: Dict[str, Any] = request.json

        messages: List[Dict[str, Any]] = data["messages"]
        city: OregonCity | None = OregonCity.from_maybe_str(data["city"])
        state: UsaState = UsaState.from_maybe_str(data["state"])

        # Create a stable & unique thread ID based on client IP and endpoint
        # TODO: consider using randomly-generated token stored client-side in
        #       a secure-cookie
        tid: str | None = None

        def generate() -> Generator[str, Any, None]:
            response_stream: Generator[ContentBlock, Any, None] = (
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

        # text/plain rather than application/x-ndjson: client only reads raw bytes
        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
