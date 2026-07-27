"""Backend configuration: LLM settings, datastores, templates, and environment parsing.

Provides a singleton configuration object (:data:`SINGLETON`) that loads and
validates all runtime settings from the environment (or .env file) at import time,
ensuring the app fails fast if required values are missing.
"""

import logging
import os
from collections.abc import Mapping
from enum import StrEnum, auto
from pathlib import Path
from typing import Final, Optional, cast

from dotenv import load_dotenv
from langchain_google_genai import HarmBlockThreshold, HarmCategory

from .logger import temporary_formatted_handler

logger = logging.getLogger(__name__)

_DATASTORE_PREFIX: Final = "VERTEX_AI_DATASTORE_"
"""Environment variable prefix for Vertex AI Search datastore IDs."""


class DatastoreKey(StrEnum):
    """Datastore keys — must match the suffix of the corresponding VERTEX_AI_DATASTORE_<NAME> env var (lowercased)."""

    LAWS = auto()
    """Datastore containing Oregon housing code and related statutes, regulations, and guidance."""

    OREGON_LAW_HELP = auto()
    """Datastore containing Oregon Law Center housing law guidance and resources for tenants and advocates."""


def _parse_datastores(env: Mapping[str, str]) -> dict[str, str]:
    """Build a datastore name→id dict from environment variables with the VERTEX_AI_DATASTORE_ prefix.

    Each variable named ``VERTEX_AI_DATASTORE_<NAME>`` becomes an entry keyed by
    ``<NAME>`` lowercased. The value may be a bare datastore ID or a full resource URI.

    Args:
        env: Environment variable mapping to parse.

    Returns:
        Dictionary mapping lowercase datastore names to datastore IDs.

    Raises:
        ValueError: If a datastore variable has no name or is empty.
    """
    result = {}
    for key, value in env.items():
        if not key.startswith(_DATASTORE_PREFIX):
            continue
        name = key.removeprefix(_DATASTORE_PREFIX).lower()
        if not name:
            raise ValueError(
                f"[{key}] datastore variable has no name after the prefix."
            )
        value = value.strip()
        if not value:
            raise ValueError(f"[{key}] environment variable is set but empty.")
        if value.startswith("projects/"):
            value = value.rstrip("/").split("/")[-1]
        result[name] = value
    return result


def _strtobool(val: Optional[str]) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1';
    False values are 'n', 'no', 'f', 'false', 'off', and '0', or None.

    Args:
        val: String value to parse as boolean, or None.

    Returns:
        True if val is a true value, False if val is a false value or None.

    Raises:
        ValueError: If val is not a recognized truth value.
    """

    if val is None:
        return False

    # credit to SO: https://stackoverflow.com/a/79879247
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"Invalid truth value {val!r}")


class _GoogEnvAndPolicy:
    """Validated Google Cloud configuration, read once from the environment.

    A single instance, :data:`SINGLETON`, is built at import time and holds every
    setting the LLM and RAG retrieval need. Required values are read from the
    environment (raising if unset or empty); the model-tuning knobs are fixed in
    code for reproducible legal output. The attributes below are the individual
    pseudo-constants exposed as ``SINGLETON.<NAME>``.
    """

    # Note: these are instance attributes stored in __slots__ (assigned in
    # __init__). The bare annotations below carry their types and docs for the
    # API reference without creating class-level values (which __slots__ forbids).
    __slots__ = (
        "MODEL_NAME",
        "VERTEX_AI_DATASTORES",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "SHOW_MODEL_THINKING",
        "SAFETY_SETTINGS",
        "MODEL_TEMPERATURE",
        "TOP_P",
        "MAX_TOKENS",
        "THINKING_BUDGET",
    )

    MODEL_NAME: str
    """Gemini model identifier (env ``MODEL_NAME``, required)."""
    VERTEX_AI_DATASTORES: dict[str, str]
    """Datastore name -> id, parsed from every ``VERTEX_AI_DATASTORE_*`` var; ``laws`` is required."""
    GOOGLE_CLOUD_PROJECT: str
    """GCP project ID (env ``GOOGLE_CLOUD_PROJECT``, required)."""
    GOOGLE_CLOUD_LOCATION: str
    """Vertex AI compute region for the LLM (env ``GOOGLE_CLOUD_LOCATION``, required)."""
    GOOGLE_APPLICATION_CREDENTIALS: str
    """GCP credentials: a file path or inline JSON (env ``GOOGLE_APPLICATION_CREDENTIALS``, required)."""
    SHOW_MODEL_THINKING: bool
    """Whether to stream model reasoning as ``ReasoningChunk``s (env ``SHOW_MODEL_THINKING``, default false)."""
    SAFETY_SETTINGS: dict
    """Gemini harm-category thresholds; all set to OFF so statutory discussion is not blocked."""
    MODEL_TEMPERATURE: float
    """Sampling temperature, fixed low (0.1) for consistent legal citation output."""
    TOP_P: float
    """Nucleus-sampling top-p, fixed low (0.1) alongside the temperature."""
    MAX_TOKENS: int
    """Maximum output tokens per response."""
    THINKING_BUDGET: int
    """Gemini thinking-token budget; ``-1`` lets the model size it dynamically."""

    def __init__(self) -> None:
        """Initialize validated Google Cloud configuration from environment.

        Loads .env file if present, then reads and validates all required environment
        variables (MODEL_NAME, project, location, credentials, datastores). Sets
        hard-coded tuning parameters (temperature, top_p, safety settings).

        Raises:
            ValueError: If any required environment variable is missing, empty, or invalid.
        """
        # Read .env at object creation time.
        path_to_env = Path(__file__).parent.parent / ".env"
        if path_to_env.exists():
            load_dotenv(dotenv_path=path_to_env, override=True)
        else:
            logger.warning(
                "No .env file found at %s, proceeding with existing environment variables.",
                path_to_env,
            )

        # Assign & Check slot attributes for required environment variables.
        # Note: assign explicitly since typecheckers do not understand slotted attributes
        #       that are assigned by __setattr__()
        _model_name = os.getenv("MODEL_NAME")
        _gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        _gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION")
        _gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        for name, value in (
            ("MODEL_NAME", _model_name),
            ("GOOGLE_CLOUD_PROJECT", _gcp_project),
            ("GOOGLE_CLOUD_LOCATION", _gcp_location),
            ("GOOGLE_APPLICATION_CREDENTIALS", _gcp_creds),
        ):
            # Catches both unset (None) and explicitly empty (e.g. VAR="").
            # Does not catch whitespace-only values.
            if not value:
                raise ValueError(
                    f"[{name}] environment variable is not set or is empty."
                )

        self.MODEL_NAME: Final[str] = cast(str, _model_name)
        self.GOOGLE_CLOUD_PROJECT: Final[str] = cast(str, _gcp_project)
        self.GOOGLE_CLOUD_LOCATION: Final[str] = cast(str, _gcp_location)
        self.GOOGLE_APPLICATION_CREDENTIALS: Final[str] = cast(str, _gcp_creds)

        # _parse_datastores raises ValueError if any matched var is set but empty.
        self.VERTEX_AI_DATASTORES: Final[dict[str, str]] = _parse_datastores(os.environ)
        if DatastoreKey.LAWS not in self.VERTEX_AI_DATASTORES:
            raise ValueError(
                f"[{_DATASTORE_PREFIX}LAWS] environment variable is not set."
            )

        # Assign slot attributes for optional environment variables
        self.SHOW_MODEL_THINKING: Final = _strtobool(
            os.getenv("SHOW_MODEL_THINKING", "false")
        )

        # Assign slot attributes for hard-coded values
        # TODO: separate these from environment variables
        self.SAFETY_SETTINGS: Final = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.OFF,
        }

        # Low temperature for consistent legal citation output.
        # Gemini 2.5 default is 0.7; Gemini 3+ defaults to 1.0.
        # https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/#langchain_google_genai.ChatGoogleGenerativeAI.temperature
        self.MODEL_TEMPERATURE: Final = float(0.1)
        self.TOP_P: Final = float(0.1)
        self.MAX_TOKENS: Final = 65535
        self.THINKING_BUDGET: Final = GEMINI_THINKING_BUDGET_DYNAMIC


GEMINI_THINKING_BUDGET_DYNAMIC: Final = -1
"""Sentinel value to let Gemini set the thinking budget dynamically based on query complexity."""

DEFAULT_VERTEX_AI_SEARCH_LOCATION: Final = "us"
"""Default multi-region location for Vertex AI Search datastores (distinct from LLM compute region)."""

with temporary_formatted_handler(logger):
    SINGLETON: Final = _GoogEnvAndPolicy()
    """Module singleton: validated Google Cloud configuration loaded at import time."""

LANGSMITH_API_KEY: Final = os.getenv("LANGSMITH_API_KEY")
"""Optional LangSmith API key for tracing (env ``LANGSMITH_API_KEY``)."""

OREGON_LAW_CENTER_PHONE_NUMBER: Final = "888-585-9638"
"""Oregon Law Center phone number provided in chatbot responses."""

RESPONSE_WORD_LIMIT: Final = 350
"""Target word limit for model responses."""

_SYSTEM_PROMPT_PATH: Final = Path(__file__).parent / "system_prompt.md"
"""File path to the system prompt template."""


def _load_system_prompt() -> str:
    """Load the system prompt from the external markdown file.

    Reads system_prompt.md and substitutes placeholders for RESPONSE_WORD_LIMIT
    and OREGON_LAW_CENTER_PHONE_NUMBER.

    Returns:
        System prompt string with placeholders substituted.

    Raises:
        FileNotFoundError: If the system prompt file cannot be read.
    """
    template = _SYSTEM_PROMPT_PATH.read_text()
    return template.format(
        RESPONSE_WORD_LIMIT=RESPONSE_WORD_LIMIT,
        OREGON_LAW_CENTER_PHONE_NUMBER=OREGON_LAW_CENTER_PHONE_NUMBER,
    )


DEFAULT_INSTRUCTIONS: Final = _load_system_prompt()
"""Default system prompt with placeholders substituted for word limit and law center phone number."""

_LETTER_TEMPLATE_PATH: Final = Path(__file__).parent / "letter_template.md"
"""File path to the letter template."""

LETTER_TEMPLATE: Final = _LETTER_TEMPLATE_PATH.read_text()
"""Letter template markdown with placeholder fields for the agent to fill in."""
