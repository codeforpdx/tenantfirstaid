import uuid
import datetime

from openai import OpenAI
import jsonlines
from flask import request, stream_with_context, Response, session, after_this_request
from flask.views import View
import os

from .shared import DEFAULT_INSTRUCTIONS, DATA_DIR

DATA_FILE = DATA_DIR / "chatlog.jsonl"

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))
BASE_URL = os.getenv("MODEL_ENDPOINT", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL_NAME", "o3")
MODEL_REASONING_EFFORT = os.getenv("MODEL_REASONING_EFFORT", "medium")


class ChatView(View):
    DATA_FILE = DATA_DIR / "chatlog.jsonl"

    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    def __init__(self, session):
        self.session = session

    # Prompt iteration idea
    # If the user starts off by saying something unclear, start off by asking me \"What are you here for?\"

    def dispatch_request(self):
        data = request.json
        user_msg = data["message"]

        # Get or create session ID using Flask sessions
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id

            @after_this_request
            def save_session(response):
                session.modified = True
                return response

        current_session = self.session.get(session_id)

        # Format messages for the new Responses API
        input_messages = []

        # Add conversation history (excluding system prompt)
        for msg in current_session["messages"][0:]:
            input_messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        input_messages.append({"role": "user", "content": user_msg})

        # Update our cache with the user message
        current_session["messages"].append({"role": "user", "content": user_msg})

        # Add city and state filters if they are set
        instructions = DEFAULT_INSTRUCTIONS
        instructions += f"\nThe user is in {current_session['city']} {current_session['state'].upper()}.\n"

        # We either want to use both city and state, or just state.
        # This filters out other cities in the same state.
        # The user is gated into selecting a city in Oregon so we don't worry about
        # whether the relevant documents exist or not.
        VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

        tools = (
            [
                {
                    "type": "file_search",
                    "vector_store_ids": [VECTOR_STORE_ID],
                    "max_num_results": os.getenv("NUM_FILE_SEARCH_RESULTS", 5),
                    "filters": {
                        "type": "or",
                        "filters": [
                            {
                                "type": "and",
                                "filters": [
                                    {
                                        "type": "eq",
                                        "key": "city",
                                        "value": current_session["city"],
                                    },
                                    {
                                        "type": "eq",
                                        "key": "state",
                                        "value": current_session["state"],
                                    },
                                ],
                            }
                            if current_session["city"] != "null"
                            else None,
                            {
                                "type": "and",
                                "filters": [
                                    {
                                        "type": "eq",
                                        "key": "city",
                                        "value": "null",
                                    },
                                    {
                                        "type": "eq",
                                        "key": "state",
                                        "value": current_session["state"],
                                    },
                                ],
                            },
                        ],
                    },
                }
            ]
            if VECTOR_STORE_ID
            else None
        )

        print("TOOLS", tools if tools else None)

        def generate():
            try:
                # Use the new Responses API with streaming
                response_stream = self.client.responses.create(
                    model=MODEL,
                    input=input_messages,
                    instructions=instructions,
                    reasoning={"effort": MODEL_REASONING_EFFORT},
                    stream=True,
                    include=["file_search_call.results"],
                    tools=tools if tools else None,
                )

                assistant_chunks = []
                for chunk in response_stream:
                    if hasattr(chunk, "delta"):
                        token = chunk.delta or ""
                        assistant_chunks.append(token)
                        yield token

                # Join the complete response
                assistant_msg = "".join(assistant_chunks)

                # Add this as a training example
                self._append_training_example(session_id, user_msg, assistant_msg)
                current_session["messages"].append(
                    {"role": "assistant", "content": assistant_msg}
                )

            except Exception as e:
                error_msg = f"Error generating response: {e}"
                print(error_msg)
                current_session["messages"].append(
                    {"role": "assistant", "content": error_msg}
                )
                yield f"Error: {str(e)}"

            finally:
                self.session.set(session_id, current_session)

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )

    def _append_training_example(self, session_id, user_msg, assistant_msg):
        # Ensure the parent directory exists
        self.DATA_FILE.parent.mkdir(exist_ok=True)

        with jsonlines.open(self.DATA_FILE, mode="a") as f:
            f.write(
                {
                    "messages": [
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant_msg},
                    ],
                    "metadata": {
                        "session_id": session_id,
                        "ts": datetime.datetime.utcnow().isoformat(),
                    },
                }
            )
