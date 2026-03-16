import os
from pathlib import Path
from typing import Final, Optional

from dotenv import load_dotenv
from langchain_google_genai import HarmBlockThreshold, HarmCategory


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
        "VERTEX_AI_DATASTORE",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "SHOW_MODEL_THINKING",
        "SAFETY_SETTINGS",
        "MODEL_TEMPERATURE",
        "MAX_TOKENS",
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
        self.VERTEX_AI_DATASTORE = os.getenv("VERTEX_AI_DATASTORE")
        self.GOOGLE_CLOUD_PROJECT: Final = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.GOOGLE_CLOUD_LOCATION: Final = os.getenv("GOOGLE_CLOUD_LOCATION")
        self.GOOGLE_APPLICATION_CREDENTIALS: Final = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

        for c in list(self.__slots__)[:5]:
            if self.__getattribute__(c) is None:
                raise ValueError(f"[{c}] environment variable is not set.")

        # FIXME: Temporary hack for VERTEX_AI_DATASTORE (old code wanted full
        #        path URI, new code only wants the last part)
        #        (https://github.com/codeforpdx/tenantfirstaid/issues/247)
        if (
            self.VERTEX_AI_DATASTORE is not None
            and "projects/" in self.VERTEX_AI_DATASTORE
        ):
            self.VERTEX_AI_DATASTORE = self.VERTEX_AI_DATASTORE.split("/")[-1]

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

        # Gemini 2.5 default is 0.7 (this was the value used before explicitly setting it)
        # Gemini 3+ will automatically set to 1.0 as per Google best practices doc.
        # https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/#langchain_google_genai.ChatGoogleGenerativeAI.temperature
        self.MODEL_TEMPERATURE: Final = float(0.7)
        self.MAX_TOKENS: Final = 65535


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
