"""
Command-line RAG chat app
  Implemented in LangChain
  Working example of user-defined Enums in BaseTool input schema
  Working example of VertexAISearchRetriever
    comments show actual/example configuration-variable values
    comments show sanity check curl command

To run:
  % uv run simple_langchain_demo.py
"""

from enum import StrEnum, auto
from pathlib import Path
from pprint import pprint
from typing import List, Optional
from warnings import warn

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool, tool
from langchain_google_community import VertexAISearchRetriever
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from tenantfirstaid.constants import DEFAULT_INSTRUCTIONS, SINGLETON


# Primitive inputs and outputs
# schema does not seem to need to include runtime/ToolRuntime arg
class SimpleToolInputSchema(BaseModel):
    """Simple Tool Input schema using primitive types"""

    x: int
    y: int


@tool(args_schema=SimpleToolInputSchema)
def simple_agent_tool(x: int, y: int, runtime: ToolRuntime) -> float:
    """compute Rayleigh scattering"""
    return 3.3


# values need to be str for JSON/Protobuf serialization, int/IntEnum do not work
class Colors(StrEnum):
    red = "Red"
    orange = "Orange"
    yellow = auto()  # mix of str and auto() doesn't seem to cause problems
    green = auto()
    blue = auto()
    indigo = "Indigo"
    violet = auto()


# some internet posts and error messages suggested 'use_enum_values=True' and 'arbitrary_types_allowed=True' config settings
# but these don't seem to be necessary
class UserDefinedEnumToolInputSchema(BaseModel):
    color: Optional[Colors]  # Optional or not seems to work
    rayleigh_coeff: float


@tool(args_schema=UserDefinedEnumToolInputSchema)
def user_defined_enum_agent_tool(
    color: Optional[Colors], rayleigh_coeff: float, runtime: ToolRuntime
) -> bool:
    """decide whether given color is a valid representation of the given coeffient"""

    if color is None:
        raise ValueError("color cannot be None")

    if color == Colors.blue and rayleigh_coeff > 3.0 and rayleigh_coeff < 4.0:
        return True
    else:
        return False


# RAG search tool
class RagToolInputSchema(BaseModel):
    query: str


@tool(args_schema=RagToolInputSchema)
def rag_tool(query: str, runtime: ToolRuntime) -> str:
    """Tool to search through Vertex Datastore"""

    # gcloud auth login
    # gcloud config set account $GMAIL@gmail.com
    # gcloud config set project tenantfirstaid
    credentials = Credentials.from_authorized_user_file(
        SINGLETON.GOOGLE_APPLICATION_CREDENTIALS
    )

    # stand-alone command to confirm credentials and environment \
    #   -> JSON result that doesn't look like an HTTP error
    # curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    #   -H "Content-Type: application/json" \
    #   "https://discoveryengine.googleapis.com/v1alpha/projects/175543967572/locations/global/collections/default_collection/engines/tenantfirstaid-corpora-sea_1758844096647/servingConfigs/default_search:search" \
    #   -d '{"query":"Oregon eviction laws", \
    #       "pageSize":10,\
    #       "queryExpansionSpec":{"condition":"AUTO"}, \
    #       "spellCorrectionSpec":{"mode":"AUTO"}, \
    #       "languageCode":"en-US", \
    #       "contentSearchSpec":{"extractiveContentSpec":{"maxExtractiveAnswerCount":1}}, \
    #       "userInfo":{"timeZone":"America/Los_Angeles"}}'

    city = "portland"
    state = "or"

    # https://console.cloud.google.com/gen-app-builder/locations/global/engines/tenantfirstaid-corpora-sea_1758844096647/data/documents?authuser=0&project=tenantfirstaid&supportedpurview=folder
    rag = VertexAISearchRetriever(
        beta=True,
        name="tfa-retriever",
        project_id=SINGLETON.GOOGLE_CLOUD_PROJECT,  # tenantfirstaid
        location_id=SINGLETON.GOOGLE_CLOUD_LOCATION,  # global
        data_store_id=SINGLETON.VERTEX_AI_DATASTORE,  # "tenantfirstaid-corpora_1758844059585",
        engine_data_type=0,  # unstructured
        get_extractive_answers=True,
        credentials=credentials,
        filter=f'''city: ANY("{city}") AND state: ANY("{state}")''',
    )

    # reveal the query from the model onto the console (stderr)
    warn(query)

    # TODO: can "filter" argument be used in invocation?
    try:
        docs: List[Document] = rag.invoke(input=query)

    except Exception as e:
        docs: List[Document] = []
        warn(f"{e}")

    return "\n".join(doc.page_content for doc in docs)


def create_and_query_agent():
    print("-" * 20)

    for s in SINGLETON.__slots__:
        pprint({s: SINGLETON.__getattribute__(s)})

    print("-" * 20)

    # TODO: checkpointer=InMemorySaver()
    llm = ChatGoogleGenerativeAI(
        model=SINGLETON.MODEL_NAME,
        temperature=SINGLETON.MODEL_TEMPERATURE,
        max_tokens=SINGLETON.MAX_TOKENS,
        project=SINGLETON.GOOGLE_CLOUD_PROJECT,
        location=SINGLETON.GOOGLE_CLOUD_LOCATION,
        safety_settings=SINGLETON.SAFETY_SETTINGS,
    )

    tools: List[BaseTool] = [simple_agent_tool, user_defined_enum_agent_tool, rag_tool]

    sys_prompt: SystemMessage = SystemMessage(
        #     content="You are a concise climate scientist."
        content=DEFAULT_INSTRUCTIONS
    )

    print("-" * 20)

    agt = create_agent(
        model=llm,
        tools=tools,
        system_prompt=sys_prompt,
    )

    human_msg = list()
    human_msg.append(
        HumanMessage(
            content="Does Oregon law allow landlords to evict tenants from their apartment?  Ground your answer with results from the RAG tool."
        )
    )

    print("-" * 20)

    for idx, chunk in enumerate(
        # TODO: multi-turn over human_msg list
        agt.stream(
            input={
                "messages": human_msg,
                "context": [],
            },
            stream_mode="updates",
        )
    ):
        # outer dict key changes with internal messages (Model, Tool, ...)
        chunk_k = list(chunk.keys())[0]
        print(f"  chunk {idx} ... {chunk_k.upper()}")

        # Specialize handling/printing based on each message class/type
        for midx, m in enumerate(chunk[chunk_k]["messages"]):
            match m:
                case AIMessage():
                    print(f"    AIMessage {idx}.{midx}")
                    print(
                        f"      {type(m)}: {m.content}"
                    )  # list(TypedDict('text', 'thought_signature'))

                    for k, v in m.response_metadata.items():
                        print(f"      msg.response_metadata.{k} = {v}")
                case ToolMessage():
                    print(f"    ToolMessage {idx}.{midx}")
                    print(f"      {m}")
                # Fall-through case
                case _:
                    print(f"{type(m)}: {m}")


if __name__ == "__main__":
    env_path: Path = Path(__file__).parent / "../.env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        FileNotFoundError(f"could not load environment from [{env_path}]")

    # instantiate Pydantic BaseModel class and dump JSON to confirm
    # whether Pydantic is able to serialize the class (independent of LangChain)
    foo = UserDefinedEnumToolInputSchema(color=Colors.indigo, rayleigh_coeff=2.7)
    print((foo.model_dump(mode="json")))

    # finally do the LangChain stuff
    create_and_query_agent()
