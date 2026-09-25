"""LangSmith tracing credentials.

Here rather than in :mod:`tenantfirstaid.constants` because nothing in the
application package reads it -- only the evaluation harness does. It stayed in
the app's configuration module long enough to make three evaluation modules
require a configured project, credentials and model in order to learn whether
tracing was available.

Unvalidated on purpose. An absent key is a legitimate state that each caller
reports in its own terms, so this is a plain read rather than a setting that
refuses to load.
"""

import os
from typing import Final

LANGSMITH_API_KEY: Final = os.getenv("LANGSMITH_API_KEY")
"""Optional LangSmith API key for tracing (env ``LANGSMITH_API_KEY``)."""
