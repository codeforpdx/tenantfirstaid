"""The application's configuration: the composition of every half of it.

Building :data:`SINGLETON` at import is what makes the app fail fast on a bad
environment, and it is also why this module holds nothing else. Importing it
costs a complete, valid environment, so anything a narrower caller might want --
the GCP identity, the datastores, the model settings, the authored text -- lives
in :mod:`~tenantfirstaid.google_auth`, :mod:`~tenantfirstaid.datastores`,
:mod:`~tenantfirstaid.google_models` and :mod:`~tenantfirstaid.constants`
respectively. Only something that needs the whole application belongs here.
"""

import logging
from typing import Final

from .datastores import DATASTORE_PREFIX, DatastoreKey, corpus_env
from .google_auth import gcp_env
from .google_models import model_env
from .logger import temporary_formatted_handler

logger = logging.getLogger(__name__)


class _AppConfig:
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
        """Compose the corpus and model configurations into the application's settings.

        Reads the GCP identity the corpus is addressed through, and the model
        settings, then flattens both onto this object so callers need not know
        which half a setting came from. Adds the one requirement neither half
        can state on its own: the
        application cannot answer a question without primary law, so
        :attr:`~tenantfirstaid.datastores.DatastoreKey.LAWS` must be configured.

        Raises:
            ValueError: If any required environment variable is missing, empty, or invalid.
        """
        # Read once and passed in, so that the identity this object exposes is
        # the same one the corpus was resolved against rather than a second read
        # that could disagree with it. gcp_env loads .env as a side effect.
        _gcp = gcp_env()
        _corpus = corpus_env(_gcp)
        # No identity argument: the model settings involve no project. The
        # identity a model call is made under is applied in graph.py, from the
        # flattened values below.
        _model = model_env()

        # Flattened rather than exposed as `.corpus` and `.model`. The layering
        # governs what a caller is required to *have*, not how it reads what it
        # has, and every caller of this object wants both halves anyway -- so
        # nesting would expose a structure they have no decision to make about.
        #
        # Note: assign explicitly since typecheckers do not understand slotted
        #       attributes that are assigned by __setattr__()
        self.GOOGLE_CLOUD_PROJECT: Final[str] = _gcp.project
        self.GOOGLE_CLOUD_LOCATION: Final[str] = _gcp.location
        self.GOOGLE_APPLICATION_CREDENTIALS: Final[str] = _gcp.credentials_source

        self.VERTEX_AI_DATASTORES: Final[dict[str, str]] = dict(_corpus.datastores)
        # Required here rather than in corpus_env, because it is a fact about this
        # application and not about the corpus configuration. `vertex_ai_search
        # --datastore <id>` reads the same configuration and needs no LAWS entry.
        if DatastoreKey.LAWS not in self.VERTEX_AI_DATASTORES:
            raise ValueError(
                f"[{DATASTORE_PREFIX}LAWS] environment variable is not set."
            )

        self.MODEL_NAME: Final[str] = _model.model_name
        self.SHOW_MODEL_THINKING: Final[bool] = _model.show_thinking
        self.SAFETY_SETTINGS: Final[dict] = _model.safety_settings
        self.MODEL_TEMPERATURE: Final[float] = _model.temperature
        self.TOP_P: Final[float] = _model.top_p
        self.MAX_TOKENS: Final[int] = _model.max_tokens
        self.THINKING_BUDGET: Final[int] = _model.thinking_budget


with temporary_formatted_handler(logger):
    SINGLETON: Final = _AppConfig()
    """Module singleton: validated Google Cloud configuration loaded at import time."""
