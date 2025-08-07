from pathlib import Path
from flask import Flask, jsonify, session
import os
import secrets

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version


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
    saved_session = tenant_session.get()
    return jsonify(saved_session["messages"])


@app.post("/api/clear-session")
def clear_session():
    session.clear()
    return jsonify({"success": True})


@app.get("/api/version")
def get_version():
    try:
        # Try the package name as defined in pyproject.toml
        app_version = version("tenant-first-aid")
        return jsonify({"version": app_version})
    except Exception:
        try:
            # Try alternative package name format
            app_version = version("tenant_first_aid")
            return jsonify({"version": app_version})
        except Exception:
            # Fallback for development or when setuptools-scm can't determine version
            # This happens when there are no git tags yet
            return jsonify({"version": "0.1.0-dev"})


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
