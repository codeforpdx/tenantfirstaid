import os

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mailman import Mail

# .chat → constants loads .env via an absolute path; do not re-load here.
from .chat import ChatView
from .feedback import send_feedback
from .logger import configure_logging

# Configure logging after .chat (→ constants → .env load) so ENV from .env is honored.
configure_logging()

app = Flask(__name__)


limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
)
# Configure CORS with strict origin validation
ALLOWED_ORIGINS = [
    "https://tenantfirstaid.com",
    "https://www.tenantfirstaid.com",
]

# Add localhost origins for development
if os.getenv("ENV", "dev") == "dev":
    ALLOWED_ORIGINS.extend(
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",  # Vite default
            "http://127.0.0.1:5173",
        ]
    )

CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# Configure Flask Mail
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = os.getenv("MAIL_PORT")
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("SENDER_EMAIL")
app.config["MAIL_PASSWORD"] = os.getenv("APP_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("SENDER_EMAIL")

mail = Mail(app)


app.add_url_rule("/api/query", view_func=ChatView.as_view("chat"), methods=["POST"])


@limiter.limit("3 per minute")
def feedback_route():
    return send_feedback()


app.add_url_rule(
    "/api/feedback",
    endpoint="feedback",
    view_func=feedback_route,
    methods=["POST"],
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
