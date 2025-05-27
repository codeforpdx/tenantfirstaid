from pathlib import Path
from flask import Flask, jsonify


if Path(".env").exists():
    from dotenv import load_dotenv

    load_dotenv(override=True)

from .chat import ChatView
from .shared import CACHE
from .prompt import get_prompt, set_prompt
from .session import TenantSession

app = Flask(__name__)

session = TenantSession()

@app.get("/api/history/<session_id>")
def history(session_id):
    return jsonify(session.get(session_id))


app.add_url_rule(
    "/api/query", view_func=ChatView.as_view("chat", session), methods=["POST"]
)
app.add_url_rule(
    "/api/prompt", endpoint="prompt_get", view_func=get_prompt, methods=["GET"]
)
app.add_url_rule(
    "/api/prompt", endpoint="prompt_post", view_func=set_prompt, methods=["POST"]
)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
