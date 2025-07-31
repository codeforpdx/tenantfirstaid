from pathlib import Path
from flask import Flask, jsonify, session
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import secrets


if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from .chat import ChatView

from .session import InitSessionView, TenantSession
from .citations import get_citation
from .feedback import send_feedback

app = Flask(__name__)
mail = Mail(app)


def build_valkey_uri():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", 6379)
    password = os.getenv("DB_PASSWORD")
    ssl = False if os.getenv("DB_USE_SSL") == "false" else True
    scheme = "rediss" if ssl else "redis"

    if password:
        return f"{scheme}://:{password}@{host}:{port}"
    return f"{scheme}://{host}:{port}"


limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=build_valkey_uri(),
)

# Configure Flask sessions
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.getenv("ENV", "dev") == "prod"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Configure Flask Mail
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("APP_PASSWORD"),
)

mail.init_app(app)


tenant_session = TenantSession()


@app.get("/api/history")
def history():
    saved_session = tenant_session.get()
    return jsonify(saved_session["messages"])


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


@limiter.limit("3 per minute")
def feedback_route():
    return send_feedback(mail)


app.add_url_rule(
    "/api/feedback",
    endpoint="feedback",
    view_func=feedback_route,
    methods=["POST"],
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
