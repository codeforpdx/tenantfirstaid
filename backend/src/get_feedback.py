import jsonlines
from collections import defaultdict
from flask import jsonify, request
import os
from shared import FEEDBACK_FILE

PASSWORD = os.getenv("FEEDBACK_PASSWORD")

def get_feedback():
    data = request.json
    password = data.get("password")
    if password !=PASSWORD :
        return jsonify({"status": "unauthorized"}), 401

    prompt_to_conversations = defaultdict(list)

    with jsonlines.open(FEEDBACK_FILE, mode='r') as reader:
        for obj in reader:
            messages = obj.get("messages", [])
            feedback = obj.get("feedback", "").strip()

            # Extract system message for prompt
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
            if not system_msg:
                continue  # skip malformed entries

            # Extract rest of conversation (excluding system message)
            conversation = [m for m in messages if m["role"] != "system"]

            prompt_to_conversations[system_msg].append({
                "conversation": conversation,
                "feedback": feedback
            })

    result = []
    for prompt, conversations in prompt_to_conversations.items():
        result.append({
            "prompt": prompt,
            "conversations": conversations
        })
        
    return jsonify({"status": "success", "feedback": result}), 200

