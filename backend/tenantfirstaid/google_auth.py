"""Establishing a Google Cloud identity: the environment, and the credentials it names.

Two halves of one job. :func:`gcp_env` reads the project, location and
credentials variables; :func:`load_gcp_credentials` turns the third of those
into a usable credential, accepting either a file path (local development) or
inline JSON (LangSmith Cloud, where secrets are injected as variable values).

Deliberately independent of :mod:`tenantfirstaid.config`, which additionally
requires the model and datastore settings the *chatbot* needs and validates the
whole set together. Code wanting only an identity was previously forced to
satisfy a contract belonging to something else, and for the corpus tooling that
was circular: ``list-artifacts`` is the command that tells you which datastores
exist, and it refused to run until ``VERTEX_AI_DATASTORE_LAWS`` already named
one. Whoever most needs the inventory is precisely whoever cannot yet satisfy
the precondition. :mod:`tenantfirstaid.config` composes this module, so each
variable still has exactly one definition.
"""

import json
import logging
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import cast

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
    raise ValueError(
        f"GOOGLE_APPLICATION_CREDENTIALS points at {raw!r}, which does not exist. "
        "If you have not authenticated on this machine yet, run: "
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
def load_env_file() -> None:
    """Load ``backend/.env`` into the process environment once, if it exists.

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

    Caching the *load* is safe where caching :func:`gcp_env` was not. This memoizes
    "has the file been read", a fact about the process; ``gcp_env`` reads
    :data:`os.environ`, which tests and callers legitimately change. Tests that
    need a fresh load call ``load_env_file.cache_clear()``.
    """
    if _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH, override=True)
    else:
        logger.warning(
            "No .env file found at %s, proceeding with existing environment variables.",
            _ENV_PATH,
        )


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


def gcp_env() -> GcpEnvironment:
    """Read and validate the GCP identity variables.

    Deliberately uncached. Reading three variables is free, and a cache here
    would make the value depend on which caller ran first -- invisible in a
    long-lived process and actively wrong in a test that sets the environment
    per case.

    Raises:
        ValueError: If any of the three variables is unset or empty.
    """
    load_env_file()
    values = {
        name: os.getenv(name)
        for name in (
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "GOOGLE_APPLICATION_CREDENTIALS",
        )
    }
    # Catches both unset (None) and explicitly empty. Reported together rather
    # than one at a time, so a fresh checkout needs one round trip instead of three.
    missing = sorted(name for name, value in values.items() if not value)
    if missing:
        raise ValueError(
            " ".join(
                f"[{name}] environment variable is not set or is empty."
                for name in missing
            )
        )
    # The check above rejected every None and every empty string, so the values are
    # str -- but that is a fact about `missing`, which a type checker cannot carry
    # back to `values`. One cast naming the whole dict states it once, where the
    # proof is visible, rather than three suppressions at the point of use.
    present = cast(dict[str, str], values)
    return GcpEnvironment(
        project=present["GOOGLE_CLOUD_PROJECT"],
        location=present["GOOGLE_CLOUD_LOCATION"],
        credentials_source=present["GOOGLE_APPLICATION_CREDENTIALS"],
    )
