# from google import genai
# from google.genai import types
from flask import current_app, request, stream_with_context, Response
from flask.views import View
import os
from .langchain_chat_manager import LangChainChatManager

MODEL = os.getenv("MODEL_NAME", "gemini-2.5-pro")

RESPONSE_WORD_LIMIT = 350


# class ChatManager:
#     def __init__(self):
#         self.client = genai.Client(vertexai=True)

#     def prepare_developer_instructions(self, city: OregonCity, state: UsaState) -> str:
#         # Add city and state filters if they are set
#         instructions = DEFAULT_INSTRUCTIONS
#         instructions += (
#             f"\nThe user is in {city.else_empty()} {state.upper()}.\n"
#         )
#         return instructions

#     def generate_gemini_chat_response(
#         self,
#         messages: list,
#         city: OregonCity,
#         state: UsaState,
#         stream=False,
#         use_tools=True,
#         instructions=None,
#         model_name=MODEL,
#     ):
#         instructions = (
#             instructions
#             if instructions
#             else self.prepare_developer_instructions(city, state)
#         )

#         formatted_messages = []

#         for message in messages:
#             formatted_messages.append(
#                 {
#                     "role": (
#                         "model"
#                         if message["role"] == "assistant" or message["role"] == "model"
#                         else "user"
#                     ),
#                     "parts": [{"text": message["content"]}],
#                 }
#             )

#         generate_content_config = types.GenerateContentConfig(
#             temperature=0,
#             top_p=0,
#             max_output_tokens=65535,
#             safety_settings=[
#                 types.SafetySetting(
#                     category=types.HarmCategory("HARM_CATEGORY_HATE_SPEECH"),
#                     threshold=types.HarmBlockThreshold("OFF"),
#                 ),
#                 types.SafetySetting(
#                     category=types.HarmCategory("HARM_CATEGORY_DANGEROUS_CONTENT"),
#                     threshold=types.HarmBlockThreshold("OFF"),
#                 ),
#                 types.SafetySetting(
#                     category=types.HarmCategory("HARM_CATEGORY_SEXUALLY_EXPLICIT"),
#                     threshold=types.HarmBlockThreshold("OFF"),
#                 ),
#                 types.SafetySetting(
#                     category=types.HarmCategory("HARM_CATEGORY_HARASSMENT"),
#                     threshold=types.HarmBlockThreshold("OFF"),
#                 ),
#             ],
#             system_instruction=[instructions],
#             thinking_config=types.ThinkingConfig(
#                 include_thoughts=os.getenv("SHOW_MODEL_THINKING", "false").lower()
#                 == "true",
#                 thinking_budget=-1,
#             ),
#             tools=[
#                 types.Tool(
#                     retrieval=types.Retrieval(
#                         vertex_ai_search=types.VertexAISearch(
#                             datastore=os.getenv("VERTEX_AI_DATASTORE"),
#                             filter=f'city: ANY("{city}") AND state: ANY("{state}")',
#                             max_results=5,
#                         )
#                     )
#                 ),
#                 types.Tool(
#                     retrieval=types.Retrieval(
#                         vertex_ai_search=types.VertexAISearch(
#                             datastore=os.getenv("VERTEX_AI_DATASTORE"),
#                             filter=f'city: ANY("null") AND state: ANY("{state}")',
#                             max_results=5,
#                         )
#                     )
#                 ),
#             ],
#         )

#         response = self.client.models.generate_content_stream(
#             model=MODEL,
#             contents=formatted_messages,
#             config=generate_content_config,
#         )

#         return response


class ChatView(View):
    def __init__(self) -> None:
        # self.chat_manager = ChatManager()
        self.chat_manager = LangChainChatManager()

    def dispatch_request(self, *args, **kwargs) -> Response:
        data = request.json
        messages = data["messages"]

        def generate():
            # response_stream = self.chat_manager.generate_gemini_chat_response(
            response_stream = self.chat_manager.generate_streaming_response(
                messages,
                data["city"],
                data["state"],
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
