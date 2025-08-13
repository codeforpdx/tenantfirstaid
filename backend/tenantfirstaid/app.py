from pathlib import Path
from flask import Flask

if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from .chat import ChatView

app = Flask(__name__)


app.add_url_rule("/api/query", view_func=ChatView.as_view("chat"), methods=["POST"])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
