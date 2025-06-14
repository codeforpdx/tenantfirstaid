from pathlib import Path
from flask import Flask, jsonify, session
import os
import secrets


if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from .chat import ChatView

from .session import InitSessionView, TenantSession
from .citations import get_citation

app = Flask(__name__)

# Configure Flask sessions
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.getenv("ENV", "dev") == "prod"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


tenant_session = TenantSession()


@app.get("/api/history")
def history():
    try:
        session_id = session.get("session_id")
        if not session_id:
            return jsonify([]), 200
        saved_session = tenant_session.get(session_id)
        if not saved_session:
            return jsonify({"error": "No session found"}), 404
        print(saved_session)
        return jsonify(saved_session["messages"]), 200
    except KeyError:
        return jsonify({"error": "Session not found"}), 404


@app.post("/api/clear-session")
def clear_session():
    session.clear()
    return jsonify({"success": True})


app.add_url_rule(
    "/api/init",
    view_func=InitSessionView.as_view("init", tenant_session),
    methods=["POST"],
)

app.add_url_rule(
    "/api/query", view_func=ChatView.as_view("chat", tenant_session), methods=["POST"]
)

app.add_url_rule(
    "/api/citation", endpoint="citation", view_func=get_citation, methods=["GET"]
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
