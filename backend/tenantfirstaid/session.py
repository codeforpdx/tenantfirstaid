import os
import uuid
from flask import Response, after_this_request, request, session
from flask.views import View
from typing import TypedDict
from valkey import Valkey
import simplejson as json
from typing import Any, Dict, Optional, Literal


class TenantSessionData(TypedDict):
    city: str
    state: str
    messages: list  # List of messages with role and content


NEW_SESSION_DATA = TenantSessionData(city="null", state="or", messages=[])


# The class to manage tenant sessions using Valkey and Flask sessions
class TenantSession:
    def __init__(self) -> None:
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
        session_id: str | None = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id
            session["site_user"] = True

            @after_this_request
            def save_session(response: Response) -> Response:
                session.modified = True
                return response

        return session_id

    def get(self) -> TenantSessionData:
        session_id = self.get_flask_session_id()

        saved_session: Optional[str] = self.db_con.get(session_id)  # type: ignore # known issue https://github.com/valkey-io/valkey-py/issues/164
        if not saved_session:
            return self.getNewSessionData()

        obj = json.loads(s=saved_session)
        return TenantSessionData(
            city=obj["city"], state=obj["state"], messages=obj["messages"]
        )

    def set(self, value: TenantSessionData) -> None:
        session_id = self.get_flask_session_id()
        self.db_con.set(session_id, json.dumps(value))

    def getNewSessionData(self) -> TenantSessionData:
        return TenantSessionData(**NEW_SESSION_DATA.copy())


# The Flask view to initialize a session
class InitSessionView(View):
    def __init__(self, tenant_session: TenantSession):
        self.tenant_session = tenant_session

    def dispatch_request(self, *args, **kwargs) -> Response:
        data: Dict[str, Any] = request.json
        session_id: Optional[str] = self.tenant_session.get_flask_session_id()

        city: str | Literal["null"] = data["city"] or "null"
        state: str = data["state"]

        # Initialize the session with city and state
        initial_data = TenantSessionData(city=city, state=state, messages=[])
        self.tenant_session.set(initial_data)

        return Response(
            status=200,
            response=json.dumps({"session_id": session_id}),
            mimetype="application/json",
        )
