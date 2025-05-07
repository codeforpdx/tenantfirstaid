import uuid
import datetime

from openai import OpenAI
import jsonlines
from flask import request, stream_with_context, Response, jsonify

from shared import CACHE

MESSAGE_CACHE = {}  # Store message content by session_id and message_id
MODEL = "o3"
DATA_FILE = "chatlog.jsonl"

client = OpenAI()


# Prompt iteration idea
# If the user starts off by saying something unclear, start off by asking me \"What are you here for?\"


SYSTEM_PROMPT = (
    "Pretend you're a lawyer who giving advice about eviction notices in Oregon. "
    "Please give shorter answers. Please only ask one question at a time so that the user isn't confused. "
    "If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed "
    "in various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center at 5131234567. "
)

def chat():
    data = request.json
    session_id = data.get("session_id") or str(uuid.uuid4())
    user_msg = data["message"]
    message_id = data.get("message_id") or str(uuid.uuid4())
    
    # Initialize new sessions with system prompt
    if not CACHE[session_id]:
        CACHE[session_id].append({"role": "system", "content": SYSTEM_PROMPT})
    
    # Format messages for the new Responses API
    input_messages = []
    
    # Add system prompt
    if CACHE[session_id] and CACHE[session_id][0]["role"] == "system":
        input_messages.append({
            "role": "system",
            "content": CACHE[session_id][0]["content"]
        })
    
    # Add conversation history (excluding system prompt)
    for msg in CACHE[session_id][1:]:
        input_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Add current user message
    input_messages.append({
        "role": "user",
        "content": user_msg
    })
    
    # Update our cache with the user message
    CACHE[session_id].append({"role": "user", "content": user_msg})
    
    # Store user message in MESSAGE_CACHE with message_id
    if session_id not in MESSAGE_CACHE:
        MESSAGE_CACHE[session_id] = {}
    MESSAGE_CACHE[session_id][message_id] = {"role": "user", "content": user_msg}

    def generate():
        try:
            # Use the new Responses API with streaming
            response_stream = client.responses.create(
                model=MODEL,
                input=input_messages,
                reasoning={"effort": "medium"},
                stream=True
            )

            assistant_chunks = []
            for chunk in response_stream:
                if hasattr(chunk, 'text'):
                    token = chunk.text or ""
                    assistant_chunks.append(token)
                    yield token

            # Join the complete response
            assistant_msg = "".join(assistant_chunks)
            CACHE[session_id].append({"role": "assistant", "content": assistant_msg})

            # Generate a response message ID and store in cache
            response_id = str(uuid.uuid4())
            MESSAGE_CACHE[session_id][response_id] = {"role": "assistant", "content": assistant_msg}

            # Add this as a training example
            _append_training_example(session_id, user_msg, assistant_msg)
            
        except Exception as e:
            print(f"Error generating response: {e}")
            yield f"Error: {str(e)}"

    return Response(stream_with_context(generate()), mimetype="text/plain")


def _append_training_example(session_id, user_msg, assistant_msg):
    with jsonlines.open(DATA_FILE, mode="a") as f:
        f.write({
            "messages": [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg}
            ],
            "metadata": {
                "session_id": session_id,
                "ts": datetime.datetime.utcnow().isoformat()
            }
        })
