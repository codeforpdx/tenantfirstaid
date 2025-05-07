from flask import request, jsonify
import os
import jsonlines
import datetime

from shared import CACHE, FEEDBACK_FILE

# Ensure feedback directory exists
os.makedirs(os.path.dirname(FEEDBACK_FILE) if os.path.dirname(FEEDBACK_FILE) else ".", exist_ok=True)

def submit_feedback():
    """
    Endpoint for submitting feedback on responses with better alternatives.
    This feedback will be used in fine-tuning to improve the model.
    """
    data = request.json
    session_id = data.get("session_id")
    comment = data.get("comment")
    
    if not all([session_id, comment]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Get the full conversation history for this session if it exists
    conversation_messages = []
    if session_id in CACHE:
        conversation_messages = CACHE[session_id]
    
    # If we don't have history, fall back to a basic version
    if not conversation_messages:
        # Store the feedback as a basic training example with the better response
        with jsonlines.open(FEEDBACK_FILE, mode="a") as f:
            f.write({
                "messages": [
                    {"role": "user", "content": "Unknown user message"},
                ],
                "metadata": {
                    "session_id": session_id,
                    "feedback_type": "user_correction",
                    "ts": datetime.datetime.utcnow().isoformat()
                },
                "feedback": comment
            })
        return jsonify({"status": "success"}), 200
    
    # Clone the conversation history to avoid modifying the cache
    training_messages = []
    for msg in conversation_messages:
        training_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Store the feedback as a training example with the full conversation context
    with jsonlines.open(FEEDBACK_FILE, mode="a") as f:
        f.write({
            "messages": training_messages,
            "metadata": {
                "session_id": session_id,
                "feedback_type": "user_correction",
                "ts": datetime.datetime.utcnow().isoformat()
            },
            "feedback": comment
        })
    
    return jsonify({"status": "success"}), 200
