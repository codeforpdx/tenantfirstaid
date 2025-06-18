import os
import uuid
from flask import Response, after_this_request, request, session
from flask.views import View
from typing import TypedDict
from valkey import Valkey
import simplejson as json


class TenantSessionMessage(TypedDict):
    role: str  # 'user' or 'assistant'
    content: str  # The content of the message


class TenantSessionData(TypedDict):
    city: str
    state: str
    messages: list[TenantSessionMessage]  # List of messages with role and content


# The class to manage tenant sessions using Valkey and Flask sessions
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

    # Retrieves the session ID from Flask session or creates a new one
    def get_flask_session_id(self) -> str:
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id

            @after_this_request
            def save_session(response):
                session.modified = True
                return response

        return session_id

    def get(self) -> TenantSessionData:
        session_id = self.get_flask_session_id()

        saved_session = self.db_con.get(session_id)
        if not saved_session:
            return self.getNewSessionData()

        return json.loads(saved_session)

    def set(self, value: TenantSessionData):
        session_id = self.get_flask_session_id()
        self.db_con.set(session_id, json.dumps(value))

    def getNewSessionData(self) -> TenantSessionData:
        return {
            "city": "",
            "state": "",
            "messages": [],
        }


# The Flask view to initialize a session
class InitSessionView(View):
    def __init__(self, tenant_session: TenantSession):
        self.tenant_session = tenant_session

    def dispatch_request(self):
        data = request.json
        session_id = self.tenant_session.get_flask_session_id()

        city = data["city"] or "null"
        state = data["state"]

        # Initialize the session with city and state
        initial_data: TenantSessionData = {"city": city, "state": state, "messages": []}
        self.tenant_session.set(initial_data)

        return Response(
            status=200,
            response=json.dumps({"session_id": session_id}),
            mimetype="application/json",
        )
