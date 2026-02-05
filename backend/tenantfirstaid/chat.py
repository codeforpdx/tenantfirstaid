"""
Module for Flask Chat View
"""

from typing import Any, Dict, Generator, List, Optional

from flask import Response, current_app, request, stream_with_context
from flask.views import View
from langchain_core.messages import (
    AnyMessage,
    ContentBlock,
)

from .langchain_chat_manager import LangChainChatManager
from .location import OregonCity, UsaState


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

        data: Dict[str, Any] = request.json

        messages: List[AnyMessage] = data["messages"]
        city: Optional[OregonCity] = OregonCity.from_maybe_str(data["city"])
        state: UsaState = UsaState.from_maybe_str(data["state"])

        # Create a stable & unique thread ID based on client IP and endpoint
        # TODO: consider using randomly-generated token stored client-side in
        #       a secure-cookie
        tid: Optional[str] = None

        def generate() -> Generator[str, Any, None]:
            response_stream: Generator[ContentBlock] = (
                self.chat_manager.generate_streaming_response(
                    messages=messages,
                    city=city,
                    state=state,
                    thread_id=tid,
                )
            )

            for content_block in response_stream:
                return_text: str = ""

                current_app.logger.debug(f"Received content_block: {content_block}")

                match content_block["type"]:
                    case "reasoning":
                        # reasoning-key is not required in the ReasoningContentBlock typed-dict
                        if "reasoning" in content_block:
                            return_text += f"\N{THINKING FACE} <em>{content_block['reasoning'].rstrip()}</em> \N{THINKING FACE}\n\n"
                    case "text":
                        # These are the Model messages back to the User
                        return_text += f"{content_block['text']}\n"

                yield return_text

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
