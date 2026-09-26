"""Establishing a Google Cloud identity: the environment, and the credentials it names.

Two halves of one job. :meth:`GcpEnvironment.from_env` reads the project,
location and credentials variables; :func:`load_gcp_credentials` turns the third
of those into a usable credential, accepting either a file path (local development) or
inline JSON (LangSmith Cloud, where secrets are injected as variable values).

Deliberately independent of :mod:`tenantfirstaid.config`, which additionally
requires the model and datastore settings the *chatbot* needs and validates the
whole set together. Code wanting only an identity was previously forced to
satisfy a contract belonging to something else -- planned corpus tooling (#318)
that only lists or manages datastores needs the same escape: it should not have
to first supply ``VERTEX_AI_DATASTORE_LAWS``, since knowing what exists is
exactly what a tool without one is trying to establish. :mod:`tenantfirstaid.config`
composes this module, so each variable still has exactly one definition.
"""

import json
import logging
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Final, Mapping

from dotenv import load_dotenv
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

_ENV_PATH = Path(__file__).parent.parent / ".env"


def discoveryengine_client_options(location: str) -> ClientOptions | None:
    """Return ClientOptions for the Discovery Engine API endpoint.

    Returns None for the "global" location so the client uses its default
    endpoint. All other locations use a regional endpoint.

    Args:
        location: GCP location ("global" or a region name).

    Returns:
        ClientOptions for the regional endpoint, or None for "global".

    See:
        https://cloud.google.com/generative-ai-app-builder/docs/locations#specify_a_multi-region_for_your_data_store
    """
    if location == "global":
        return None
    return ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")


def _parse_inline_json(raw: str) -> dict:
    """Parse inline JSON, with a helpful error message on failure.

    Args:
        raw: JSON string to parse.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        ValueError: If the string is not valid JSON.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        preview = "*" * 40 + "(redacted, secret is too short to preview)"

        # Show the first 40 chars to help diagnose without leaking the full secret.
        if len(raw) > 80:
            preview = raw[:40] + "..."
        raise ValueError(
            f"GOOGLE_APPLICATION_CREDENTIALS is not a valid file path and "
            f"could not be parsed as JSON: {e}. "
            f"Value starts with: {preview!r}"
        ) from e


_MAX_ECHOED_PATH_CHARS: Final = 200
"""Longest value :func:`_shorten` will quote in full.

A path long enough to exceed this is not a path anyone typed, so the cost of
truncating it is nil -- and the bound is what keeps an unforeseen encoding of a
secret from reaching the logs whole, rather than the shape tests alone.
"""


def _shorten(raw: str) -> str:
    """Bound how much of ``raw`` an error message may quote."""
    if len(raw) <= _MAX_ECHOED_PATH_CHARS:
        return raw
    return f"{raw[:40]}... ({len(raw)} characters)"


def _looks_like_a_path(raw: str) -> bool:
    """Whether ``raw`` has the shape of a filesystem path rather than a secret.

    A separator alone does not qualify: standard base64's alphabet includes
    "/", so a base64-encoded key can contain one. Base64 never contains ".",
    so this requires one alongside a separator -- or a ".json" suffix on its
    own, the common case for a credentials file.
    """
    if raw.endswith(".json"):
        return True
    return "." in raw and ("/" in raw or "\\" in raw)


def _reject_missing_credentials_file(raw: str) -> None:
    """Fail plainly when the value names a file that is not there.

    Without this the value falls through to the inline-JSON branch and is
    reported as a JSON parse error with its content redacted -- which describes
    neither the problem nor anything the reader can act on. The overwhelmingly
    common cause is that ``gcloud auth application-default login`` has never been
    run on this machine, or its output was moved, so the message names that.

    The path is shown rather than redacted. Redaction exists because the variable
    may hold a credential *value*; a path that resolves to nothing is not one, and
    hiding it removes the only detail that identifies the mistake.
    """
    # The value is echoed below, so this must fire only on something that cannot
    # be a credential. Inline JSON always contains whitespace and quote
    # characters and a filesystem path essentially never does, which separates
    # the two without relying on a leading brace -- a *truncated* secret may not
    # have one, and that is precisely the value that must not be echoed.
    if any(c.isspace() or c == '"' for c in raw) or not raw:
        return
    # A base64-encoded service-account key, which some secret stores inject,
    # passes the test above: its alphabet holds neither whitespace nor quotes,
    # and can contain "/" -- so a separator alone does not prove this is a path.
    if not _looks_like_a_path(raw):
        return
    raise ValueError(
        f"GOOGLE_APPLICATION_CREDENTIALS points at {_shorten(raw)!r}, which does "
        "not exist. If you have not authenticated on this machine yet, run: "
        "mise run //:gcloud-login"
    )


def load_gcp_credentials(
    raw: str,
) -> Credentials | service_account.Credentials:
    """Load GCP credentials from a file path or inline JSON string.

    Accepts either a path to a credentials file (the traditional approach)
    or the JSON content itself (for environments like LangSmith Cloud where
    secrets are injected as env var values, not files).

    Args:
        raw: File path to credentials JSON or the JSON string itself.

    Returns:
        Credentials or ServiceAccountCredentials object.

    Raises:
        ValueError: If credentials cannot be parsed or type is unsupported.
    """
    # Try as a file path first. Guard against OSError for strings that are
    # too long or otherwise invalid as paths (e.g. inline JSON blobs).
    try:
        cred_path = Path(raw)
        if cred_path.is_file():
            with cred_path.open("r") as f:
                info = json.load(f)
        else:
            _reject_missing_credentials_file(raw)
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
    # Unreachable: the wildcard case above is exhaustive and always raises.
    # The assertion silences CodeQL py/mixed-returns (implicit None return warning).
    raise AssertionError("unreachable")  # pragma: no cover


@cache
def load_env_file() -> Mapping[str, str]:
    """Load ``backend/.env`` once, if it exists, and return the resulting environment.

    Safe to call from either entry point: the corpus scripts reach GCP without ever
    building the application configuration, so neither module can assume the other
    ran first. Each therefore calls this, and the cache makes the redundant calls
    free.

    Cached to take a **one-time snapshot**, which is the behaviour this had when it
    was a side effect of importing the configuration module, and which the split
    into per-caller reads would otherwise have lost. Two reasons it matters, beyond
    not re-reading a file on every call:

    - ``override=True`` means the file wins over the ambient environment. Applied
      once at startup that is the intent; applied repeatedly it silently reverts
      anything a caller has since set in :data:`os.environ`.
    - A ``.env`` edited while the process runs would otherwise take effect
      part-way through it, so two reads of the same variable could disagree.

    The returned mapping is that snapshot: the ambient environment with the file
    applied over it. Every ``from_env`` reads from it rather than calling
    :func:`os.getenv`, so a group of related settings is read from one consistent
    view. A few call sites still read :data:`os.environ` directly (``app.py``'s
    mail config and ``ENV`` check, ``feedback.py``, ``logger.py``'s log level) --
    this is where *those* readers would read from too, not a guarantee that none
    remain. Tests that need a fresh load call ``load_env_file.cache_clear()``;
    the suite does so between every test.

    The process environment is still mutated, because third-party libraries read
    it directly and cannot be handed the mapping -- ``langsmith`` picks up
    ``LANGSMITH_TRACING`` and ``LANGCHAIN_TRACING_V2`` itself. So this returns a
    view *in addition to* loading, not instead of it.

    Returns:
        A read-only view of the environment as of the load. Read-only because a
        caller mutating it would change what every other reader sees while
        leaving :data:`os.environ` untouched, so the two would disagree.
    """
    if _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH, override=True)
    else:
        logger.warning(
            "No .env file found at %s, proceeding with existing environment variables.",
            _ENV_PATH,
        )
    return MappingProxyType(dict(os.environ))


@dataclass(frozen=True)
class GcpEnvironment:
    """The three settings needed to authenticate to GCP and name a project."""

    project: str
    """GCP project ID (env ``GOOGLE_CLOUD_PROJECT``)."""
    location: str
    """GCP region (env ``GOOGLE_CLOUD_LOCATION``)."""
    credentials_source: str
    """Credentials as a file path or inline JSON (env ``GOOGLE_APPLICATION_CREDENTIALS``).

    The raw value rather than a loaded credential, because loading performs I/O
    and can fail for reasons — a missing file, a revoked token — that a caller
    may want to report differently from a missing variable.
    """

    def load_credentials(self) -> "Credentials | service_account.Credentials":
        """Load the credentials this environment names.

        Raises:
            ValueError: If the value is neither a readable credentials file nor
                parseable inline JSON.
        """
        return load_gcp_credentials(self.credentials_source)

    @classmethod
    def from_env(cls) -> "GcpEnvironment":
        """Read and validate the GCP identity variables.

        Raises:
            ValueError: If any of the three variables is unset or empty.
        """
        env = load_env_file()
        # Stripped so that a value of "  " is treated as unset rather than carried
        # into a resource path, and so a path with a stray trailing newline works.
        values = {
            name: (env.get(name) or "").strip()
            for name in (
                "GOOGLE_CLOUD_PROJECT",
                "GOOGLE_CLOUD_LOCATION",
                "GOOGLE_APPLICATION_CREDENTIALS",
            )
        }
        # Reported together rather than one at a time, so a fresh checkout needs one
        # round trip instead of three.
        missing = sorted(name for name, value in values.items() if not value)
        if missing:
            raise ValueError(
                " ".join(
                    f"[{name}] environment variable is not set or is empty."
                    for name in missing
                )
            )
        return cls(
            project=values["GOOGLE_CLOUD_PROJECT"],
            location=values["GOOGLE_CLOUD_LOCATION"],
            credentials_source=values["GOOGLE_APPLICATION_CREDENTIALS"],
        )
