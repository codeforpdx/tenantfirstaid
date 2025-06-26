from openai.types.responses.easy_input_message_param import EasyInputMessageParam
from openai import OpenAI
from openai.types.shared_params import (
    ComparisonFilter,
    CompoundFilter,
    Reasoning,
    ReasoningEffort,
)
from openai.types.responses import (
    FileSearchToolParam,
    Response as ResponseEvent,
    ResponseIncludable,
    ResponseInputParam,
    ResponseStreamEvent,
    ResponseTextDeltaEvent,
)
from flask import request, stream_with_context, Response
from flask.views import View
import os
from typing_extensions import Literal, overload

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))
BASE_URL = os.getenv("MODEL_ENDPOINT", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL_NAME", "o3")
reasoning_effort = os.getenv("MODEL_REASONING_EFFORT")
MODEL_REASONING_EFFORT: ReasoningEffort = "medium"
match reasoning_effort:
    case "low":
        MODEL_REASONING_EFFORT = "low"
    case "medium":
        MODEL_REASONING_EFFORT = "medium"
    case "high":
        MODEL_REASONING_EFFORT = "high"


OREGON_LAW_CENTER_PHONE_NUMBER = "888-585-9638"
DEFAULT_INSTRUCTIONS = f"""Pretend you're a legal expert who is giving advice about eviction notices in Oregon.
Please give shorter answers. 
Please only ask one question at a time so that the user isn't confused. 
If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed in various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center at {OREGON_LAW_CENTER_PHONE_NUMBER}.
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
    def __init__(self):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
        )

    def get_client(self):
        return self.client

    def prepare_developer_instructions(self, city: str, state: str):
        # Add city and state filters if they are set
        instructions = DEFAULT_INSTRUCTIONS
        instructions += f"\nThe user is in {city} {state.upper()}.\n"
        return instructions

    def prepare_openai_tools(self, city: str, state: str) -> list | None:
        VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
        if not VECTOR_STORE_ID:
            return None

        # We either want to use both city and state, or just state.
        # This filters out other cities in the same state.
        # The user is gated into selecting a city in Oregon so we don't worry about
        # whether the relevant documents exist or not.
        FILTER_STATE_IS_OREGON = ComparisonFilter(type="eq", key="state", value="or")
        FILTER_CITY_IS_NULL = ComparisonFilter(type="eq", key="city", value="null")
        FILTER_CITY_IS_GIVEN = ComparisonFilter(type="eq", key="city", value=city)
        FILTER_OREGON_AND_NULL_CITY = CompoundFilter(
            type="and", filters=[FILTER_STATE_IS_OREGON, FILTER_CITY_IS_NULL]
        )
        FILTER_OREGON_AND_SOME_CITY = CompoundFilter(
            type="and", filters=[FILTER_STATE_IS_OREGON, FILTER_CITY_IS_GIVEN]
        )
        FILTER_UNION = CompoundFilter(
            type="or",
            filters=[FILTER_OREGON_AND_NULL_CITY, FILTER_OREGON_AND_SOME_CITY],
        )
        if city != "null":
            filters = FILTER_UNION
        else:
            filters = FILTER_OREGON_AND_NULL_CITY

        print("Preparing OpenAI tools with filters:", filters)

        max_num_results = int(os.getenv("NUM_FILE_SEARCH_RESULTS", 10))

        return [
            FileSearchToolParam(
                type="file_search",
                vector_store_ids=[VECTOR_STORE_ID],
                max_num_results=max_num_results,
                filters=filters,
            )
        ]

    from typing import Iterator, Union

    # With streaming response
    @overload
    def generate_chat_response(
        self, messages: ResponseInputParam, city: str, state: str, stream: Literal[True]
    ) -> Iterator[ResponseStreamEvent]: ...

    # No streaming response
    @overload
    def generate_chat_response(
        self,
        messages: ResponseInputParam,
        city: str,
        state: str,
        stream: Literal[False],
    ) -> ResponseEvent: ...

    def generate_chat_response(
        self, messages: ResponseInputParam, city: str, state: str, stream: bool
    ):
        instructions = self.prepare_developer_instructions(city, state)
        tools = self.prepare_openai_tools(city, state)
        param_includes: list[ResponseIncludable] = ["file_search_call.results"]

        # Use the OpenAI client to generate a response
        response_stream = self.client.responses.create(
            model=MODEL,
            input=messages,
            instructions=instructions,
            reasoning=Reasoning(effort=MODEL_REASONING_EFFORT),
            stream=stream,
            include=param_includes,
            tools=tools if tools else [],
        )

        return response_stream


class ChatView(View):
    def __init__(self, tenant_session):
        self.tenant_session = tenant_session
        self.chat_manager = ChatManager()

    def dispatch_request(self, *args, **kwargs):
        data = request.json
        user_msg = data["message"]

        current_session = self.tenant_session.get()
        current_session["messages"].append(
            EasyInputMessageParam(role="user", content=user_msg)
        )

        def generate():
            # Use the new Responses API with streaming
            response_stream = self.chat_manager.generate_chat_response(
                current_session["messages"],
                current_session["city"],
                current_session["state"],
                stream=True,
            )

            assistant_chunks = []
            for event in response_stream:
                if isinstance(event, ResponseTextDeltaEvent):
                    # Append the content of the assistant message chunk
                    assistant_chunks.append(event.delta)
                    yield event.delta

            # Join the complete response
            assistant_msg = "".join(assistant_chunks)

            current_session["messages"].append(
                {"role": "system", "content": assistant_msg}
            )

            self.tenant_session.set(current_session)

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
