from pathlib import Path
from flask import Flask, jsonify


if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from .chat import ChatView
from .submit_feedback import submit_feedback
from .get_feedback import get_feedback
from .session import TenantSession

app = Flask(__name__)

session = TenantSession()

@app.get("/api/history/<session_id>")
def history(session_id):
    return jsonify(session.get(session_id))


app.add_url_rule(
    "/api/query", view_func=ChatView.as_view("chat", session), methods=["POST"]
)
app.add_url_rule("/api/get_feedback", view_func=get_feedback, methods=["POST"])
app.add_url_rule("/api/feedback", view_func=submit_feedback, methods=["POST"])


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
