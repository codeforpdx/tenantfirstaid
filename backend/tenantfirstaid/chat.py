import vertexai
from vertexai.preview import rag
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    Tool,
)
from google.oauth2 import service_account
from flask import request, stream_with_context, Response
from flask.views import View
import os

API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY"))
BASE_URL = os.getenv("MODEL_ENDPOINT", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL_NAME", "gemini-2.5-pro")

OREGON_LAW_CENTER_PHONE_NUMBER = "888-585-9638"
DEFAULT_INSTRUCTIONS = f"""Pretend you're a legal expert who is giving advice about housing and tenants' rights in Oregon.
Please give shorter answers. 
Please only ask one question at a time so that the user isn't confused. 
If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed in various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center at {OREGON_LAW_CENTER_PHONE_NUMBER}.
Focus on finding technicalities that would legally prevent someone getting evicted, such as deficiencies in notice.
Assume the user is on a month-to-month lease unless they specify otherwise.

Use only the information from the file search results to answer the question.
City codes will override the state codes if there is a conflict.

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
"""


class ChatManager:
    def __init__(self):
        creds = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_FILE", "google-service-account.json")
        )
        vertexai.init(
            project="tenantfirstaid",
            location="us-west1",
            credentials=creds,
        )

    def prepare_developer_instructions(self, city: str, state: str):
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

        model = GenerativeModel(
            model_name=model_name,
            system_instruction=instructions,
        )

        formatted_messages = []

        for message in messages:
            formatted_messages.append(
                {
                    "role": "model"
                    if message["role"] == "assistant" or message["role"] == "model"
                    else "user",
                    "parts": [{"text": message["content"]}],
                }
            )

        
        GEMINI_RAG_CORPUS = os.getenv("GEMINI_RAG_CORPUS")
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(
                            rag_corpus=GEMINI_RAG_CORPUS
                        )
                    ]
                )
            )
        )

        response = model.generate_content(
            contents=formatted_messages,
            stream=stream,
            generation_config=GenerationConfig(temperature=0.2),
            tools=[rag_retrieval_tool] if use_tools else None,
        )

        return response


class ChatView(View):
    def __init__(self, tenant_session):
        self.tenant_session = tenant_session
        self.chat_manager = ChatManager()

    def dispatch_request(self, *args, **kwargs):
        data = request.json
        user_msg = data["message"]

        current_session = self.tenant_session.get()
        current_session["messages"].append(dict(role="user", content=user_msg))

        def generate():
            # Use the new Responses API with streaming
            response_stream = self.chat_manager.generate_gemini_chat_response(
                current_session["messages"],
                current_session["city"],
                current_session["state"],
                stream=True,
            )
            
            

            assistant_chunks = []
            for event in response_stream:
                assistant_chunks.append(event.candidates[0].content.parts[0].text)
                yield event.candidates[0].content.parts[0].text

            # Join the complete response
            assistant_msg = "".join(assistant_chunks)

            current_session["messages"].append(
                {"role": "model", "content": assistant_msg}
            )

            self.tenant_session.set(current_session)

        return Response(
            stream_with_context(generate()),
            mimetype="text/plain",
        )
