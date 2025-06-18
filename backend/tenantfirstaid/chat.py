from pathlib import Path
from openai import OpenAI
from flask import request, stream_with_context, Response
from flask.views import View
import os

from .session import TenantSessionData, TenantSessionMessage

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))
BASE_URL = os.getenv("MODEL_ENDPOINT", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL_NAME", "o3")
MODEL_REASONING_EFFORT = os.getenv("MODEL_REASONING_EFFORT", "medium")

DEFAULT_INSTRUCTIONS = """Pretend you're a legal expert who giving advice about eviction notices in Oregon. 
Please give shorter answers. 
Please only ask one question at a time so that the user isn't confused. 
If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed in various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center at 5131234567. 
Focus on finding technicalities that would legally prevent someone getting evicted, such as deficiencies in notice.
Assume the user is on a month-to-month lease unless they specify otherwise.

Use only the information from the file search results to answer the question.
City codes will override the state codes if there is a conflict.

Make sure to include a citation to the relevant law in your answer, with a link to the actual web page the law is on using HTML.
Use the following websites for citation links:
https://oregon.public.law/statutes
https://www.portland.gov/code/30/01
https://eugene.municipal.codes/EC/8.425
Include the links inline in your answer, with the attribute target="_blank" so that they open in a new tab, likethis:
<a href="https://oregon.public.law/statutes/ORS_90.427" target="_blank">ORS 90.427</a>.
"""


class ChatManager:
    def __init__(self, tenant_session: TenantSessionData = None):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
        )
        self.tenant_session = tenant_session

    def get_client(self):
        return self.client

    def prepare_developer_instructions(self, city: str, state: str):
        # Add city and state filters if they are set
        instructions = DEFAULT_INSTRUCTIONS
        instructions += f"\nThe user is in {city} {state.upper()}.\n"
        return instructions

    def prepare_openai_tools(self, city: str, state: str):
        VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
        if not VECTOR_STORE_ID:
            return None

        # We either want to use both city and state, or just state.
        # This filters out other cities in the same state.
        # The user is gated into selecting a city in Oregon so we don't worry about
        # whether the relevant documents exist or not.
        filters = (
            {
                "type": "or",
                "filters": [
                    {
                        "type": "and",
                        "filters": [
                            {
                                "type": "eq",
                                "key": "city",
                                "value": city,
                            },
                            {
                                "type": "eq",
                                "key": "state",
                                "value": state,
                            },
                        ],
                    },
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
                                "value": state,
                            },
                        ],
                    },
                ],
            }
            if city != "null"
            else {
                # If city is null, we only filter by state
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
                        "value": state,
                    },
                ],
            }
        )

        return [
            {
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID],
                "max_num_results": os.getenv("NUM_FILE_SEARCH_RESULTS", 10),
                "filters": filters,
            }
        ]

    def generate_chat_response(
        self, messages: list[TenantSessionMessage], city: str, state: str, stream=False
    ):
        instructions = self.prepare_developer_instructions(city, state)
        tools = self.prepare_openai_tools(city, state)

        # Use the OpenAI client to generate a response
        response_stream = self.client.responses.create(
            model=MODEL,
            input=messages,
            instructions=instructions,
            reasoning={"effort": MODEL_REASONING_EFFORT},
            stream=stream,
            include=["file_search_call.results"],
            tools=tools if tools else None,
        )

        return response_stream


class ChatView(View):
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )

    def __init__(self, tenant_session):
        self.tenant_session = tenant_session
        self.chat_manager = ChatManager()

    def dispatch_request(self):
        data = request.json
        user_msg = data["message"]

        current_session = self.tenant_session.get()
        current_session["messages"].append({"role": "user", "content": user_msg})

        def generate():
            try:
                # Use the new Responses API with streaming
                response_stream = self.chat_manager.generate_chat_response(
                    current_session["messages"],
                    current_session["city"],
                    current_session["state"],
                    stream=True,
                )

                assistant_chunks = []
                for chunk in response_stream:
                    if hasattr(chunk, "delta"):
                        token = chunk.delta or ""
                        assistant_chunks.append(token)
                        yield token

                # Join the complete response
                assistant_msg = "".join(assistant_chunks)

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
                self.tenant_session.set(current_session)

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
