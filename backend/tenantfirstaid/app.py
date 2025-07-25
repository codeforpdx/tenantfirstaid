from pathlib import Path
from flask import Flask, jsonify, session, request
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import os
import secrets


if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from .chat import ChatView

from .session import InitSessionView, TenantSession
from .citations import get_citation

app = Flask(__name__)
mail = Mail(app)

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


def send_feedback():
    feedback = request.form.get("feedback")
    file = request.files.get("transcript")

    if not file:
        return "No file provided", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join("/tmp", filename)
    file.save(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        html_content = f.read()

    msg = Message(
        subject="Feedback with Transcript",
        sender=os.getenv("MAIL_USERNAME"),
        recipients=["michael@qiu-qiulaw.com"],
        body=f"User feedback:\n\n{feedback}",
    )
    msg.attach(
        filename="transcript.html",
        content_type="text/html",
        data=html_content.encode("utf-8"),
    )

    mail.send(msg)
    os.remove(filepath)

    return "Email sent", 200


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

app.add_url_rule(
    "/api/feedback", endpoint="feedback", view_func=send_feedback, methods=["POST"]
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
