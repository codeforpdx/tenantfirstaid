from valkey import Valkey
import simplejson as json
from .shared import CONFIG
from ipaddress import IPv4Address


class TenantSession:
    def __init__(self):
        _valkey_args = {
            "host": IPv4Address(CONFIG.db_host),
            "port": CONFIG.db_port,
            "password": CONFIG.db_password,
            "ssl": CONFIG.db_use_ssl,
        }

        print(
            f"Connecting to Valkey: {_valkey_args}",
        )
        try:
            self.db_con = Valkey(**_valkey_args)
            self.db_con.ping()

        except Exception as e:
            print(e)

    def get(self, session_id):
        return json.loads(self.db_con.get(session_id) or "[]")

    def set(self, session_id, value):
        self.db_con.set(session_id, json.dumps(value))
