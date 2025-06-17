from flask import Flask, jsonify, session as flask_session
import os
import secrets

from .chat import ChatView

from .session import TenantSession
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
    session_id = flask_session.get("session_id")
    if not session_id:
        return jsonify([])
    return jsonify(tenant_session.get(session_id))


@app.post("/api/clear-session")
def clear_session():
    flask_session.clear()
    return jsonify({"success": True})


app.add_url_rule(
    "/api/query", view_func=ChatView.as_view("chat", tenant_session), methods=["POST"]
)

app.add_url_rule(
    "/api/citation", endpoint="citation", view_func=get_citation, methods=["GET"]
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
