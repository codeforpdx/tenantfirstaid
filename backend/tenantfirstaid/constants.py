import json
import os
from pathlib import Path
from typing import Final, Optional

from dotenv import load_dotenv
from langchain_google_genai import HarmBlockThreshold, HarmCategory
from pydantic import BaseModel, field_validator


class DataStoreConfig(BaseModel):
    """Configuration for a single Vertex AI Search datastore."""

    name: str
    id: str
    max_documents: int = 3

    @field_validator("name", "id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("id")
    @classmethod
    def _strip_resource_uri(cls, v: str) -> str:
        """Accept either a bare datastore ID or a full resource URI."""
        if v.startswith("projects/"):
            return v.rstrip("/").split("/")[-1]
        return v


def _parse_datastores(raw: Optional[str]) -> dict[str, DataStoreConfig]:
    """Parse a JSON array of datastore configs into a dict keyed by name."""
    if raw is None:
        raise ValueError("[VERTEX_AI_DATASTORES] environment variable is not set.")
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"VERTEX_AI_DATASTORES is not valid JSON: {e}") from e
    if not isinstance(items, list) or not items:
        raise ValueError("VERTEX_AI_DATASTORES must be a non-empty JSON array.")
    configs = [DataStoreConfig(**item) for item in items]
    names = [c.name for c in configs]
    if len(names) != len(set(names)):
        raise ValueError("VERTEX_AI_DATASTORES contains duplicate names.")
    return {c.name: c for c in configs}


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

        # Assign & Check slot attributes for required environment variables
        # Note: assign explicitly since typecheckers do not understand slotted attributes
        #       that are assigned by __setattr__()
        self.MODEL_NAME: Final = os.getenv("MODEL_NAME")
        self.GOOGLE_CLOUD_PROJECT: Final = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.GOOGLE_CLOUD_LOCATION: Final = os.getenv("GOOGLE_CLOUD_LOCATION")
        self.GOOGLE_APPLICATION_CREDENTIALS: Final = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

        for c in (
            "MODEL_NAME",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ):
            if getattr(self, c) is None:
                raise ValueError(f"[{c}] environment variable is not set.")

        # _parse_datastores raises ValueError if the var is missing, not valid JSON,
        # or resolves full resource URIs to bare datastore IDs.
        self.VERTEX_AI_DATASTORES: Final[dict[str, DataStoreConfig]] = (
            _parse_datastores(os.getenv("VERTEX_AI_DATASTORES"))
        )
        if "laws" not in self.VERTEX_AI_DATASTORES:
            raise ValueError(
                "VERTEX_AI_DATASTORES is missing required datastore: 'laws'."
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
