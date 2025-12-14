"""
Module for Flask Chat View
"""

from typing import Any, Dict, List, Optional

from flask import Response, current_app, request, stream_with_context
from flask.views import View

from .langchain_chat_manager import LangChainChatManager
from .location import OregonCity, UsaState


class ChatView(View):
    def __init__(self) -> None:
        self.chat_manager = LangChainChatManager()

    def dispatch_request(self, *args, **kwargs) -> Response:
        data: Dict[str, Any] = request.json
        messages: List[Any] = data["messages"]

        def generate():
            city: Optional[OregonCity] = OregonCity.from_maybe_str(data["city"])
            state: UsaState = UsaState.from_maybe_str(data["state"])

            response_stream = self.chat_manager.generate_streaming_response(
                messages,
                city=city,
                state=state,
                # stream=True,
            )

            assistant_chunks = []
            for event in response_stream:
                current_app.logger.debug(f"Received event: {event}")
                return_text = ""

                if event.candidates is None:
                    continue

                for candidate in event.candidates:
                    for part in candidate.content.parts:
                        return_text += f"{'<i>' if part.thought else ''}{part.text}{'</i>' if part.thought else ''}"

                assistant_chunks.append(return_text)
                yield return_text

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
