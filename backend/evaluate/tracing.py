"""LangSmith tracing credentials.

Here rather than in :mod:`tenantfirstaid.config` because nothing in the
application package reads it -- only the evaluation harness does. It stayed in
the app's configuration module long enough to make three evaluation modules
require a configured project, credentials and model in order to learn whether
tracing was available.
"""

from dataclasses import dataclass
from typing import Optional

from tenantfirstaid.google_auth import load_env_file


@dataclass(frozen=True)
class LangsmithConfig:
    """What the evaluation harness needs in order to reach LangSmith."""

    api_key: Optional[str]
    """LangSmith API key (env ``LANGSMITH_API_KEY``), or ``None`` when unset.

    Unvalidated on purpose. An absent key is a legitimate state that each caller
    reports in its own terms, so this is a plain read rather than a setting that
    refuses to load.
    """

    @classmethod
    def from_env(cls) -> "LangsmithConfig":
        """Read the LangSmith settings from the environment.

        The sibling of :meth:`~tenantfirstaid.google_auth.GcpEnvironment.from_env`,
        :meth:`~tenantfirstaid.datastores.CorpusConfig.from_env` and
        :meth:`~tenantfirstaid.google_models.ModelConfig.from_env`, and reads the
        same snapshot each of those does.

        Callers reach this through the module rather than binding the value at
        import, so the environment is read when a client is built. Two things
        follow. Importing an evaluation module requires no configuration at all,
        which is what lets the dataset CLI do offline JSONL work on a bare
        checkout; and the suite has a single place to substitute, instead of one
        patch per module that happened to bind the constant.
        """
        return cls(api_key=load_env_file().get("LANGSMITH_API_KEY"))
