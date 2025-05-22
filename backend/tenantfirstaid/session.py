import os
from valkey import Valkey
import simplejson as json


class TenantSession:
    def __init__(self):
        print("Connecting to Valkey:", {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "ssl": os.getenv("DB_USE_SSL"),
        })
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
        from flask import current_app
        current_app.logger.info(f"""self.db_con: {self.db_con} \n 
{os.getenv("DB_HOST")} 
{os.getenv("DB_PORT")} 
{os.getenv("DB_USE_SSL")
        }""")
        print(f"""self.db_con: {self.db_con} \n 
{os.getenv("DB_HOST")} 
{os.getenv("DB_PORT")} 
{os.getenv("DB_USE_SSL")
        }""")
        print("self.db_con", self.db_con)
        return json.loads(self.db_con.get(session_id) or "[]")

    def set(self, session_id, value):
        self.db_con.set(session_id, json.dumps(value))
        
    def get_document_context(self, session_id):
        """
        Retrieve document context for a session if it exists.
        This contains metadata about documents that have been uploaded and analyzed.
        """
        key = f"{session_id}_document_context"
        context = self.db_con.get(key)
        return json.loads(context) if context else None
        
    def set_document_context(self, session_id, document_data):
        """
        Store document context for a session.
        
        Args:
            session_id: The session identifier
            document_data: Dictionary containing document metadata and analysis
        """
        key = f"{session_id}_document_context"
        self.db_con.set(key, json.dumps(document_data))
