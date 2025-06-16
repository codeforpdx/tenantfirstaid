import uuid
import datetime

from openai import OpenAI
import jsonlines
from flask import request, stream_with_context, Response, session, after_this_request
from flask.views import View
import os
from typing import List

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

        VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
        NUM_FILE_SEARCH_RESULTS = os.getenv("NUM_FILE_SEARCH_RESULTS", 10)

        self.openai_tools = []

        if VECTOR_STORE_ID:
            self.openai_tools.append(
                {
                    "type": "file_search",
                    "vector_store_ids": [VECTOR_STORE_ID],
                    "max_num_results": NUM_FILE_SEARCH_RESULTS,
                }
            )

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
        for msg in current_session[0:]:
            input_messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        input_messages.append({"role": "user", "content": user_msg})

        # Update our cache with the user message
        current_session.append({"role": "user", "content": user_msg})

        def generate():
            try:
                # Use the new Responses API with streaming
                response_stream = self.client.responses.create(
                    model=MODEL,
                    input=input_messages,
                    instructions=DEFAULT_INSTRUCTIONS,
                    reasoning={"effort": MODEL_REASONING_EFFORT},
                    stream=True,
                    tools=self.openai_tools,
                )

                chunk_times: List[datetime.datetime] = [
                    datetime.datetime.now(datetime.timezone.utc)
                ]
                assistant_chunks = []
                for chunk in response_stream:
                    if hasattr(chunk, "delta"):
                        chunk_times.append(datetime.datetime.now(datetime.timezone.utc))
                        token = chunk.delta or ""
                        assistant_chunks.append(token)
                        yield token

                # Join the complete response
                assistant_msg = "".join(assistant_chunks)
                # print("assistant_msg", assistant_msg)

                # Add this as a training example
                self._append_training_example(
                    session_id, user_msg, assistant_msg, chunk_times
                )
                current_session.append({"role": "assistant", "content": assistant_msg})

            except Exception as e:
                error_msg = f"Error generating response: {e}"
                print(error_msg)
                current_session.append({"role": "assistant", "content": error_msg})
                yield f"Error: {str(e)}"

            finally:
                self.session.set(session_id, current_session)

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )

    def _append_training_example(
        self, session_id, user_msg, assistant_msg, chunk_times: List[datetime.datetime]
    ):
        # Ensure the parent directory exists
        self.DATA_FILE.parent.mkdir(exist_ok=True)

        with jsonlines.open(self.DATA_FILE, mode="a") as f:
            now: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
            f.write(
                {
                    "messages": [
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": assistant_msg},
                    ],
                    "metadata": {
                        "session_id": session_id,
                        "model": MODEL,
                        "model_reasoning_effort": MODEL_REASONING_EFFORT,
                        "chunk_times": [
                            t.isoformat(timespec="milliseconds") for t in chunk_times
                        ],
                        "ts": now.isoformat(timespec="milliseconds"),
                    },
                }
            )

            # print interesting stats in the console
            print(
                f"{(len(chunk_times) - 1):1} chunks\n",
                f"{(chunk_times[1] - chunk_times[0]).total_seconds():6.3f} first chunk time (seconds)\n",
                f"{((now - chunk_times[1]).total_seconds()) / len(chunk_times[1:]):6.3f} average chunk time after first chunk (seconds)\n",
                f"{(now - chunk_times[0]).total_seconds():6.3f} total seconds\n",
            )
