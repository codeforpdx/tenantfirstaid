import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from chat import chat, CACHE
from submit_feedback import submit_feedback
load_dotenv(override=True)

app = Flask(__name__)

@app.get("/api/history/<session_id>")
def history(session_id):
    return jsonify(CACHE.get(session_id, []))

app.add_url_rule("/api/query", view_func=chat, methods=["POST"])
app.add_url_rule("/api/feedback", view_func=submit_feedback, methods=["POST"])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
