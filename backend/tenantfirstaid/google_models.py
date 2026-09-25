"""The model half of the configuration: which Gemini model, and how to call it.

Apart from :mod:`tenantfirstaid.config` for the same reason
:class:`~tenantfirstaid.datastores.CorpusConfig` is: importing that module builds
the application singleton, so anything living there is unreachable without a
complete app environment. A sibling that can only be had by taking the whole
configuration is not a sibling.

Nothing consumes this half alone today -- every model caller also retrieves. It
lives here so that the two halves are addressable on the same terms, and so that
the family-specific work described on :class:`Gemini25ModelConfig` has somewhere
to go.
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Optional

from langchain_google_genai import HarmBlockThreshold, HarmCategory


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


@dataclass(frozen=True)
class Gemini25ModelConfig:
    """Which Gemini model to call and how to call it: everything generation needs.

    The sibling of :class:`~tenantfirstaid.datastores.CorpusConfig`. Only the
    application composes both, because only it both retrieves and generates.

    The two siblings are not the same shape, and the difference is not an
    oversight. ``CorpusConfig`` carries a :class:`~tenantfirstaid.google_auth.GcpEnvironment`
    because a datastore is addressed *through* an identity -- the project and
    region are part of its resource path. Nothing here is: these are the
    arguments to a model call, and the identity that call is made under is
    supplied by whoever builds the client. Carrying one anyway would be symmetry
    with no reader, which is the thing this split was meant to stop doing.

    Every field below the model name is fixed in code rather than read from the
    environment, so the tuning is reproducible across deployments. ``MODEL_NAME``
    is the exception, and the pairing is uneasy: the model is a variable while its
    settings are constants, and nothing checks that the two agree.

    The name says 2.5 because the shape is 2.5's, not merely the values: a later
    family does not want different numbers here, it wants different fields.
    :attr:`thinking_budget` is the clearest case: ``ThinkingConfig`` in the pinned
    SDK carries both a ``thinking_budget`` token count and a discrete
    ``thinking_level``, and 3.x expects the latter, so the field itself does not
    survive the transition. :attr:`temperature` is the subtler one, fixed low here
    for citation consistency against a 2.5 default of 0.7, where 3.x defaults to
    1.0 and is not meant to be lowered.

    Pointing ``MODEL_NAME`` at a later family therefore silently keeps 2.5-shaped
    settings. No base class is extracted yet, because there is nothing to share it
    with and the shape of the split is better decided against a real second family
    than guessed at now. What the name buys in the meantime is that the mismatch is
    visible at the point of use rather than only in this docstring.
    """

    model_name: str
    """Gemini model identifier (env ``MODEL_NAME``, required)."""
    show_thinking: bool
    """Whether to stream model reasoning as ``ReasoningChunk``s (env ``SHOW_MODEL_THINKING``)."""
    safety_settings: dict
    """Gemini harm-category thresholds; all set to OFF so statutory discussion is not blocked."""
    temperature: float
    """Sampling temperature, fixed low for consistent legal citation output."""
    top_p: float
    """Nucleus-sampling top-p, fixed low alongside the temperature."""
    max_tokens: int
    """Maximum output tokens per response."""
    THINKING_BUDGET_DYNAMIC: ClassVar[int] = -1
    """Sentinel for :attr:`thinking_budget`: let Gemini size it by query complexity.

    A class attribute rather than a module constant because it is meaningless
    apart from the field it qualifies, and because it is 2.5-shaped -- a
    family that expresses thinking as a discrete level has no use for it, and
    would simply not inherit it.
    """

    thinking_budget: int
    """Gemini thinking-token budget; see :attr:`THINKING_BUDGET_DYNAMIC`."""


def model_env() -> Gemini25ModelConfig:
    """Read the model configuration from the environment.

    Deliberately not named for a family, unlike the class it returns. Choosing
    which family ``MODEL_NAME`` denotes is this function's job, so it is the one
    thing here that survives a second family arriving -- at which point its return
    type becomes a shared base and this dispatches between the children.

    Takes no identity argument, unlike
    :func:`~tenantfirstaid.datastores.corpus_env`: reading the model settings
    involves no project, so requiring one would make a caller prove an
    environment it does not need.

    Raises:
        ValueError: If ``MODEL_NAME`` is unset or empty, or ``SHOW_MODEL_THINKING``
            is not a recognized truth value. Never for a missing datastore.
    """
    model_name = os.getenv("MODEL_NAME")
    # Catches both unset (None) and explicitly empty (e.g. VAR="").
    # Does not catch whitespace-only values.
    if not model_name:
        raise ValueError("[MODEL_NAME] environment variable is not set or is empty.")

    return Gemini25ModelConfig(
        model_name=model_name,
        show_thinking=_strtobool(os.getenv("SHOW_MODEL_THINKING", "false")),
        safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.OFF,
            HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.OFF,
        },
        # Low temperature for consistent legal citation output.
        # Gemini 2.5 default is 0.7; Gemini 3+ defaults to 1.0.
        # https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/#langchain_google_genai.ChatGoogleGenerativeAI.temperature
        temperature=float(0.1),
        top_p=float(0.1),
        max_tokens=65535,
        thinking_budget=Gemini25ModelConfig.THINKING_BUDGET_DYNAMIC,
    )
