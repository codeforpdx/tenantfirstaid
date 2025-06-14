import os
import uuid
from flask import Response, request, session
from flask.views import View
from valkey import Valkey
import simplejson as json


class TenantSession:
    def __init__(self):
        print(
            "Connecting to Valkey:",
            {
                "host": os.getenv("DB_HOST"),
                "port": os.getenv("DB_PORT"),
                "ssl": os.getenv("DB_USE_SSL"),
            },
        )
        try:
            self.db_con = Valkey(
                host=os.getenv("DB_HOST", "127.0.0.1"),
                port=os.getenv("DB_PORT", 6379),
                password=os.getenv("DB_PASSWORD"),
                ssl=False if os.getenv("DB_USE_SSL") == "false" else True,
            )
            self.db_con.ping()

        except Exception as e:
            print(e)

    def get(self, session_id):
        print("SESSION_ID", session_id)
        return json.loads(
            self.db_con.get(session_id) or '{"city": "", "state": "", "messages": []}'
        )

    def set(self, session_id, value):
        self.db_con.set(session_id, json.dumps(value))


class InitSessionView(View):
    def __init__(self, session: TenantSession):
        self.session = session

    def dispatch_request(self):
        data = request.json
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id
        city = data["city"]
        state = data["state"]

        # Initialize the session with city and state
        initial_data = {"city": city, "state": state, "messages": []}
        self.session.set(session_id, initial_data)

        return Response(
            status=200,
            response=json.dumps({"session_id": session_id}),
            mimetype="application/json",
        )
