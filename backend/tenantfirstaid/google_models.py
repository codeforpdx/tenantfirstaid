"""The model half of the configuration: which Gemini model, and how to call it.

Apart from :mod:`tenantfirstaid.config` for the same reason
:class:`~tenantfirstaid.datastores.CorpusConfig` is: importing that module builds
the application singleton, so anything living there needs a complete app
environment to reach.
"""

from dataclasses import dataclass
from typing import ClassVar, Mapping, Optional

from langchain_google_genai import HarmBlockThreshold, HarmCategory

from .google_auth import load_env_file


def _strtobool(val: Optional[str]) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1';
    False values are 'n', 'no', 'f', 'false', 'off', and '0', or None.
    Surrounding whitespace is stripped before matching.

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
    val = val.strip().lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"Invalid truth value {val!r}")


@dataclass(frozen=True)
class ModelConfig:
    """What every Gemini family needs in order to be called.

    The sibling of :class:`~tenantfirstaid.datastores.CorpusConfig`, which only
    the application composes with. It carries no
    :class:`~tenantfirstaid.google_auth.GcpEnvironment` because a model call's
    identity comes from whoever builds the client, where a datastore's is part of
    its resource path.

    Only settings that survive a change of family belong here; one whose *field* a
    later family would not want goes on that family's class instead.
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

        ``env`` is the snapshot :meth:`from_env` already took, passed on so that a
        family reads the same view the dispatch did.
        """
        raise NotImplementedError

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Read the model configuration from the environment.

        Dispatches over :data:`_FAMILIES` and refuses anything no family claims,
        so an unsupported ``MODEL_NAME`` fails at startup rather than silently
        running on another family's settings.

        Raises:
            ValueError: If ``MODEL_NAME`` is unset or empty, or
                ``SHOW_MODEL_THINKING`` is not a recognized truth value. Never for
                a missing datastore.
            NotImplementedError: If ``MODEL_NAME`` names a family this code does
                not implement.
        """
        env = load_env_file()
        # Stripped so a value like " gemini-2.5-pro" resolves rather than failing
        # the prefix match below with a confusing "unsupported family" error --
        # the same treatment GcpEnvironment.from_env gives its variables.
        model_name = (env.get("MODEL_NAME") or "").strip()
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

    Every value apart from ``MODEL_NAME`` is fixed in code, so the tuning is
    reproducible across deployments.

    :attr:`thinking_budget` is here rather than on the base because 3.x expresses
    thinking as a discrete ``thinking_level``, so the field itself does not
    survive the transition.
    """

    MODEL_NAME_PREFIX: ClassVar[str] = "gemini-2.5"
    """Matches ``gemini-2.5-pro``, ``gemini-2.5-flash`` and the rest of the family."""

    THINKING_BUDGET_DYNAMIC: ClassVar[int] = -1
    """Sentinel for :attr:`thinking_budget`: let Gemini size it by query complexity.

    On the class rather than at module level because it is meaningless apart from
    the 2.5-shaped field it qualifies.
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

Explicit rather than ``ModelConfig.__subclasses__()``, so support is stated rather
than inferred from which modules happen to have been imported.
"""
