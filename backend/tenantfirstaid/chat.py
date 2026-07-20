"""HTTP request handling for chat streaming.

Provides :class:`ChatView`, a Flask view that backs the ``POST /api/query`` endpoint.
Processes incoming chat messages and user location, drives the LangChain agent,
and streams the response as newline-delimited JSON chunks.
"""

from typing import Any, Dict, Generator, List

from flask import Response, current_app, request, stream_with_context
from flask.views import View
from langchain_core.messages import AnyMessage, ContentBlock

from .langchain_chat_manager import LangChainChatManager
from .location import OregonCity, UsaState
from .schema import (
    EndOfStreamChunk,
    LetterChunk,
    ReasoningChunk,
    ResponseChunk,
    TextChunk,
)


def _classify_blocks(
    stream: Generator[ContentBlock, Any, None],
) -> Generator[ResponseChunk, Any, None]:
    """Convert raw LangChain content blocks into typed [`ResponseChunk`](`~schema.ResponseChunk`) objects."""
    for content_block in stream:
        match content_block["type"]:
            case "reasoning":
                yield ReasoningChunk(content=content_block["reasoning"])
            case "text":
                yield TextChunk(content=content_block["text"])
            case "non_standard":
                # Tool-emitted chunks are wrapped in NonStandardContentBlock.
                # Add a case here for each tool chunk type (e.g. letter, citation).
                inner: Dict[str, Any] = content_block["value"]
                match inner.get("type"):
                    case "letter":
                        current_app.logger.debug(
                            "Routing non_standard block to letter."
                        )
                        yield LetterChunk(content=inner["content"])
                    case _:
                        current_app.logger.warning(
                            f"Unhandled non_standard block type: {inner.get('type')}"
                        )
            case _:
                # Unknown LLM block types are intentionally dropped.
                current_app.logger.warning(
                    f"Unhandled block type: {content_block['type']}"
                )


class ChatView(View):
    """Flask view backing ``POST /api/query``.

    Reads the message history and ``city``/``state`` from the request body, drives
    :class:`~tenantfirstaid.langchain_chat_manager.LangChainChatManager`, and
    streams the classified :data:`~tenantfirstaid.schema.ResponseChunk` objects
    back as newline-delimited JSON, closing with an ``EndOfStreamChunk``.
    """

    def __init__(self) -> None:
        """Initialize the ChatView with a LangChainChatManager instance."""
        self.chat_manager = LangChainChatManager()

    def dispatch_request(self, *args: Any, **kwargs: Any) -> Response:
        """Handle client POST request.

        Reads the JSON body containing chat messages and user location,
        drives the LangChainChatManager to process them, and streams the
        response as newline-delimited JSON chunks.

        Args:
            *args: Positional arguments from Flask routing (unused).
            **kwargs: Keyword arguments from Flask routing (unused).

        Returns:
            Response: Flask response streaming newline-delimited JSON chunks.

        Raises:
            KeyError: If required fields (messages, state) are missing from request body.

        Note:
            Expected JSON body uses [`OregonCity`](`~location.OregonCity`) and [`UsaState`](`~location.UsaState`) for location context.
        """

        data: Dict[str, Any] = request.json
        """Extracts messages, city, and state from the request JSON.
        Uses [`OregonCity.from_maybe_str`](`~location.OregonCity.from_maybe_str`) and [`UsaState.from_maybe_str`](`~location.UsaState.from_maybe_str`) to convert the city and state strings into their respective enum types.
        """

        messages: List[AnyMessage | Dict[str, Any]] = data["messages"]
        """List of messages from the frontend, each message is either an AnyMessage or a dictionary with keys "role", "content", and "id".
        This list is passed to the LangChainChatManager to generate a response.
        """
        city: OregonCity | None = OregonCity.from_maybe_str(data["city"])
        """User's [`city`](`~location.OregonCity`), if in Oregon and recognized by the backend. None if not recognized or not provided."""
        state: UsaState = UsaState.from_maybe_str(data["state"])
        """User's [`state`](`~location.UsaState`), if recognized by the backend. Defaults to [`UsaState.OTHER`](`~location.UsaState`) if not recognized or not provided."""

        # Create a stable & unique thread ID based on client IP and endpoint
        # TODO: consider using randomly-generated token stored client-side in
        #       a secure-cookie
        tid: str | None = None
        """Thread ID for the chat session, generated based on client IP and endpoint.
        This ID is used to maintain context across multiple messages in the same chat session.
        """

        def generate() -> Generator[str, Any, None]:
            """Generator function that streams the response chunks as newline-delimited JSON."""
            response_stream: Generator[ContentBlock, Any, None] = (
                self.chat_manager.generate_streaming_response(
                    messages=messages,
                    city=city,
                    state=state,
                    thread_id=tid,
                )
            )
            for content_block in _classify_blocks(response_stream):
                current_app.logger.debug(f"Sending content_block: {content_block}")
                yield content_block.model_dump_json() + "\n"
            done_chunk = EndOfStreamChunk()
            current_app.logger.debug(f"Sending done chunk: {done_chunk}")
            yield done_chunk.model_dump_json() + "\n"

        # text/plain rather than application/x-ndjson: client only reads raw bytes
        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
