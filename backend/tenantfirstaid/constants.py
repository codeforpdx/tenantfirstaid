import os
from collections.abc import Mapping
from enum import StrEnum, auto
from pathlib import Path
from typing import Final, Optional, cast

from dotenv import load_dotenv
from langchain_google_genai import HarmBlockThreshold, HarmCategory

_DATASTORE_PREFIX = "VERTEX_AI_DATASTORE_"


class DatastoreKey(StrEnum):
    """Datastore keys — must match the suffix of the corresponding VERTEX_AI_DATASTORE_<NAME> env var (lowercased)."""

    LAWS = auto()
    OREGON_LAW_HELP = auto()


def _parse_datastores(env: Mapping[str, str]) -> dict[str, str]:
    """Build a datastore name→id dict from environment variables with the VERTEX_AI_DATASTORE_ prefix.

    Each variable named ``VERTEX_AI_DATASTORE_<NAME>`` becomes an entry keyed by
    ``<NAME>`` lowercased. The value may be a bare datastore ID or a full resource URI.
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
    False values are 'n', 'no', 'f', 'false', 'off', and '0'.  Also None.
    Raises ValueError if 'val' is anything else.
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
    """Validate and set Google Cloud variables from OS environment"""

    # Note: these are Class variables, not instance variables.
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

    def __init__(self) -> None:
        """
        Initialization steps
        1. override environment if .env provided (otherwise variables, aka secrets, should already be set)
        2. explicitly set each slotted attribute
        3. check that the slotted attributes are not None
        """
        # read .env at object creation time
        path_to_env = Path(__file__).parent / "../.env"
        if path_to_env.exists():
            load_dotenv(override=True)

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


# Sentinel value for the Gemini API's thinking_budget parameter: -1 means
# the model sets the budget dynamically based on query complexity.
GEMINI_THINKING_BUDGET_DYNAMIC: Final = -1

# Module singleton
# TODO: rename to VERTEX_CONFIG?
SINGLETON: Final = _GoogEnvAndPolicy()

LANGSMITH_API_KEY: Final = os.getenv("LANGSMITH_API_KEY")

OREGON_LAW_CENTER_PHONE_NUMBER: Final = "888-585-9638"
RESPONSE_WORD_LIMIT: Final = 350

_SYSTEM_PROMPT_PATH: Final = Path(__file__).parent / "system_prompt.md"


def _load_system_prompt() -> str:
    """Load the system prompt from the external markdown file.

    The file uses {RESPONSE_WORD_LIMIT} and {OREGON_LAW_CENTER_PHONE_NUMBER}
    placeholders which are substituted at load time.
    """
    template = _SYSTEM_PROMPT_PATH.read_text()
    return template.format(
        RESPONSE_WORD_LIMIT=RESPONSE_WORD_LIMIT,
        OREGON_LAW_CENTER_PHONE_NUMBER=OREGON_LAW_CENTER_PHONE_NUMBER,
    )


DEFAULT_INSTRUCTIONS: Final = _load_system_prompt()

_LETTER_TEMPLATE_PATH: Final = Path(__file__).parent / "letter_template.md"
LETTER_TEMPLATE: Final = _LETTER_TEMPLATE_PATH.read_text()
