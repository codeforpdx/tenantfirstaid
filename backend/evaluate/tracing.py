"""LangSmith tracing credentials.

Here rather than in :mod:`tenantfirstaid.config` because only the evaluation
harness reads it, and reaching it through the app's configuration would make an
evaluation module require a project, credentials and a model it never uses.
"""

from dataclasses import dataclass
from typing import Optional

from tenantfirstaid.google_auth import load_env_file


@dataclass(frozen=True)
class LangsmithConfig:
    """What the evaluation harness needs in order to reach LangSmith."""

    api_key: Optional[str]
    """LangSmith API key (env ``LANGSMITH_API_KEY``), or ``None`` when unset.

    Unvalidated: an absent key is a legitimate state each caller reports in its
    own terms.
    """

    @classmethod
    def from_env(cls) -> "LangsmithConfig":
        """Read the LangSmith settings from the same snapshot its siblings read.

        Call this where a client is built rather than binding the result at
        import, so that importing an evaluation module needs no configuration --
        which is what lets the dataset CLI do offline work on a bare checkout.
        """
        return cls(api_key=load_env_file().get("LANGSMITH_API_KEY"))
