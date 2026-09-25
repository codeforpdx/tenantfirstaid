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

from dataclasses import dataclass
from typing import ClassVar, Mapping, Optional

from langchain_google_genai import HarmBlockThreshold, HarmCategory

from .google_auth import load_env_file


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
class ModelConfig:
    """What every Gemini family needs in order to be called.

    The sibling of :class:`~tenantfirstaid.datastores.CorpusConfig`. Only the
    application composes both, because only it both retrieves and generates.

    The two siblings are not the same shape, and the difference is not an
    oversight. ``CorpusConfig`` carries a :class:`~tenantfirstaid.google_auth.GcpEnvironment`
    because a datastore is addressed *through* an identity -- the project and
    region are part of its resource path. Nothing here is: these are the
    arguments to a model call, and the identity that call is made under is
    supplied by whoever builds the client. Carrying one anyway would be symmetry
    with no reader, which is the thing this split was meant to stop doing.

    Only the settings that survive a change of family live here. A setting whose
    *field* a later family would not want belongs on that family's class instead,
    which is why :attr:`Gemini25ModelConfig.thinking_budget` is not here.
    """

    MODEL_NAME_PREFIX: ClassVar[str]
    """The ``MODEL_NAME`` prefix this family answers to; see :meth:`from_env`."""

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

    @classmethod
    def _for_model_name(cls, model_name: str, env: Mapping[str, str]) -> "ModelConfig":
        """Build this family's settings for ``model_name``, reading ``env`` for any rest.

        Each family supplies its own values, because they are the family's
        knowledge rather than the reader's. ``env`` is the snapshot
        :meth:`from_env` already took, passed on so a family reads the same view.
        """
        raise NotImplementedError

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Read the model configuration from the environment.

        On the base rather than on a family, because choosing which family
        ``MODEL_NAME`` denotes is the part that survives a second family
        arriving. Dispatches over :data:`_FAMILIES` and refuses anything no
        family claims, so pointing ``MODEL_NAME`` at an unsupported model fails
        at startup rather than silently running it on another family's settings.

        Takes no identity argument, unlike
        :meth:`~tenantfirstaid.datastores.CorpusConfig.from_env`: reading the
        model settings involves no project, so requiring one would make a caller
        prove an environment it does not need.

        Raises:
            ValueError: If ``MODEL_NAME`` is unset or empty, or
                ``SHOW_MODEL_THINKING`` is not a recognized truth value. Never for
                a missing datastore.
            NotImplementedError: If ``MODEL_NAME`` names a family this code does
                not implement.
        """
        env = load_env_file()
        model_name = env.get("MODEL_NAME")
        # Catches both unset (None) and explicitly empty (e.g. VAR="").
        # Does not catch whitespace-only values.
        if not model_name:
            raise ValueError(
                "[MODEL_NAME] environment variable is not set or is empty."
            )

        for family in _FAMILIES:
            if model_name.startswith(family.MODEL_NAME_PREFIX):
                return family._for_model_name(model_name, env)
        supported = ", ".join(f.MODEL_NAME_PREFIX for f in _FAMILIES)
        raise NotImplementedError(
            f"[MODEL_NAME] {model_name!r} is not a supported model family. "
            f"Supported: {supported}."
        )


@dataclass(frozen=True)
class Gemini25ModelConfig(ModelConfig):
    """The Gemini 2.5 family: settings whose *shape*, not merely whose values, is 2.5's.

    Every field here and on the base is fixed in code rather than read from the
    environment, so the tuning is reproducible across deployments. ``MODEL_NAME``
    is the exception, and the pairing is uneasy: the model is a variable while its
    settings are constants, and nothing checks that the two agree beyond the
    prefix :meth:`~ModelConfig.from_env` dispatches on.

    A later family does not want different numbers, it wants different fields.
    :attr:`thinking_budget` is the clearest case: ``ThinkingConfig`` in the pinned
    SDK carries both a ``thinking_budget`` token count and a discrete
    ``thinking_level``, and 3.x expects the latter, so the field itself does not
    survive the transition -- which is why it is here and not on the base.
    :attr:`~ModelConfig.temperature` is the subtler one, fixed low for citation
    consistency against a 2.5 default of 0.7, where 3.x defaults to 1.0 and is not
    meant to be lowered. It stays on the base because the field survives even
    though this value does not.
    """

    MODEL_NAME_PREFIX: ClassVar[str] = "gemini-2.5"
    """Matches ``gemini-2.5-pro``, ``gemini-2.5-flash`` and the rest of the family."""

    THINKING_BUDGET_DYNAMIC: ClassVar[int] = -1
    """Sentinel for :attr:`thinking_budget`: let Gemini size it by query complexity.

    A class attribute rather than a module constant because it is meaningless
    apart from the field it qualifies, and because it is 2.5-shaped -- a
    family that expresses thinking as a discrete level has no use for it, and
    would simply not inherit it.
    """

    thinking_budget: int
    """Gemini thinking-token budget; see :attr:`THINKING_BUDGET_DYNAMIC`."""

    @classmethod
    def _for_model_name(
        cls, model_name: str, env: Mapping[str, str]
    ) -> "Gemini25ModelConfig":
        return cls(
            model_name=model_name,
            show_thinking=_strtobool(env.get("SHOW_MODEL_THINKING", "false")),
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
            thinking_budget=cls.THINKING_BUDGET_DYNAMIC,
        )


_FAMILIES: tuple[type[ModelConfig], ...] = (Gemini25ModelConfig,)
"""Every family this code implements, in the order ``from_env`` tries them.

A list rather than ``ModelConfig.__subclasses__()``, so that what is supported is
stated rather than inferred from which modules happen to have been imported.
"""
