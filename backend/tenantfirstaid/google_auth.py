"""GCP credential loading.

Supports both file-path credentials (local development) and inline JSON
(LangSmith Cloud, where secrets are injected as environment variable values).
"""

import json
from pathlib import Path

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials


def _parse_inline_json(raw: str) -> dict:
    """Parse inline JSON, with a helpful error message on failure."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Show the first 40 chars to help diagnose without leaking the full secret.
        preview = "*" * 40 + "(redacted, secret is too short to preview)"
        if len(raw) > 80:
            preview = raw[:40] + ("..." if len(raw) > 40 else "")
        raise ValueError(
            f"GOOGLE_APPLICATION_CREDENTIALS is not a valid file path and "
            f"could not be parsed as JSON: {e}. "
            f"Value starts with: {preview!r}"
        ) from e


def load_gcp_credentials(
    raw: str,
) -> Credentials | service_account.Credentials:
    """Load GCP credentials from a file path or inline JSON string.

    Accepts either a path to a credentials file (the traditional approach)
    or the JSON content itself (for environments like LangSmith Cloud where
    secrets are injected as env var values, not files).
    """
    # Try as a file path first. Guard against OSError for strings that are
    # too long or otherwise invalid as paths (e.g. inline JSON blobs).
    try:
        cred_path = Path(raw)
        if cred_path.is_file():
            with cred_path.open("r") as f:
                info = json.load(f)
        else:
            info = _parse_inline_json(raw)
    except OSError:
        # Not a valid path — treat as inline JSON.
        info = _parse_inline_json(raw)

    match info.get("type"):
        case "authorized_user":
            return Credentials.from_authorized_user_info(info)
        case "service_account":
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        case other:
            raise ValueError(f"Unsupported credential type: {other}")
