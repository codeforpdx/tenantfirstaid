from google import genai
from google.genai import types
from flask import current_app, request, stream_with_context, Response
from flask.views import View
import os

MODEL = os.getenv("MODEL_NAME", "gemini-2.5-pro")

OREGON_LAW_CENTER_PHONE_NUMBER = "888-585-9638"
DEFAULT_INSTRUCTIONS = f"""Pretend you're a legal expert who is giving advice about housing and tenants' rights in Oregon.
Please give full, detailed answers. 
Please only ask one question at a time so that the user isn't confused. 
If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed in various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center at {OREGON_LAW_CENTER_PHONE_NUMBER}.
Focus on finding technicalities that would legally prevent someone getting evicted, such as deficiencies in notice.
Assume the user is on a month-to-month lease unless they specify otherwise.

Use only the information from the file search results to answer the question.
City laws will override the state laws if there is a conflict. Make sure that if the user is in a specific city, you check for relevant city laws.

Only answer questions about housing law in Oregon, do not answer questions about other states or topics unrelated to housing law.

Do not start your response with a sentence like "As a legal expert, I can provide some information on...". Just go right into the answer. Do not call yourself a legal expert in your response.

Make sure to include a citation to the relevant law in your answer, with a link to the actual web page the law is on using HTML.
Use the following websites for citation links:
https://oregon.public.law/statutes
https://www.portland.gov/code/30/01
https://eugene.municipal.codes/EC/8.425
Include the links inline in your answer, with the attribute target="_blank" so that they open in a new tab, likethis:
<a href="https://oregon.public.law/statutes/ORS_90.427" target="_blank">ORS 90.427</a>.

If the user asks questions about Section 8 or the HomeForward program, search the web for the correct answer and provide a link to the page you used, using the same format as above.

If the user asks to make/generate/create/draft a letter, you should return a formatted letter after your conversational response. Add a delimiter -----generate letter----- to separate the two content. You can include <a>, <em>, and <strong> tags for additional formatting.
"""


class ChatManager:
    def __init__(self):
        self.client = genai.Client(vertexai=True)

    def prepare_developer_instructions(self, city: str, state: str) -> str:
        # Add city and state filters if they are set
        instructions = DEFAULT_INSTRUCTIONS
        instructions += (
            f"\nThe user is in {city if city != 'null' else ''} {state.upper()}.\n"
        )
        return instructions

    def generate_gemini_chat_response(
        self,
        messages: list,
        city: str,
        state: str,
        stream=False,
        use_tools=True,
        instructions=None,
        model_name=MODEL,
    ):
        instructions = (
            instructions
            if instructions
            else self.prepare_developer_instructions(city, state)
        )

        formatted_messages = []

        for message in messages:
            formatted_messages.append(
                {
                    "role": (
                        "model"
                        if message["role"] == "assistant" or message["role"] == "model"
                        else "user"
                    ),
                    "parts": [{"text": message["content"]}],
                }
            )

        city = city.lower() if city is not None else None
        state = state.lower() if state is not None else None

        generate_content_config = types.GenerateContentConfig(
            temperature=0,
            top_p=0,
            max_output_tokens=65535,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory("HARM_CATEGORY_HATE_SPEECH"),
                    threshold=types.HarmBlockThreshold("OFF"),
                ),
                types.SafetySetting(
                    category=types.HarmCategory("HARM_CATEGORY_DANGEROUS_CONTENT"),
                    threshold=types.HarmBlockThreshold("OFF"),
                ),
                types.SafetySetting(
                    category=types.HarmCategory("HARM_CATEGORY_SEXUALLY_EXPLICIT"),
                    threshold=types.HarmBlockThreshold("OFF"),
                ),
                types.SafetySetting(
                    category=types.HarmCategory("HARM_CATEGORY_HARASSMENT"),
                    threshold=types.HarmBlockThreshold("OFF"),
                ),
            ],
            system_instruction=[instructions],
            thinking_config=types.ThinkingConfig(
                include_thoughts=os.getenv("SHOW_MODEL_THINKING", "false").lower()
                == "true",
                thinking_budget=-1,
            ),
            tools=[
                types.Tool(
                    retrieval=types.Retrieval(
                        vertex_ai_search=types.VertexAISearch(
                            datastore=os.getenv("VERTEX_AI_DATASTORE"),
                            filter=f'city: ANY("{city}") AND state: ANY("{state}")',
                            max_results=5,
                        )
                    )
                ),
                types.Tool(
                    retrieval=types.Retrieval(
                        vertex_ai_search=types.VertexAISearch(
                            datastore=os.getenv("VERTEX_AI_DATASTORE"),
                            filter=f'city: ANY("null") AND state: ANY("{state}")',
                            max_results=5,
                        )
                    )
                ),
            ],
        )

        response = self.client.models.generate_content_stream(
            model=MODEL,
            contents=formatted_messages,
            config=generate_content_config,
        )

        return response


class ChatView(View):
    def __init__(self) -> None:
        self.chat_manager = ChatManager()

    def dispatch_request(self, *args, **kwargs) -> Response:
        data = request.json
        messages = data["messages"]

        def generate():
            response_stream = self.chat_manager.generate_gemini_chat_response(
                messages,
                data["city"],
                data["state"],
                stream=True,
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
