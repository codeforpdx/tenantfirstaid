"""Root conftest: the one thing that has to happen before anything is imported.

Separate from ``tests/conftest.py`` purely for ordering. pytest imports the
rootdir's conftest first, and the work below has to precede every other import
in the session -- including ``tests/conftest.py``'s own, one of which reaches
:func:`~tenantfirstaid.google_auth.load_env_file` and caches the result.
"""

import os
from pathlib import Path

if os.environ.get("TFA_TEST_IGNORE_ENV_FILE") == "1":
    # ``mise run test --no-env`` asked to reproduce CI, which has no ``.env``. A
    # developer machine does, and ``load_dotenv(override=True)`` means the file
    # beats every value the task exported -- so without this, a test that passes
    # only because the developer holds real credentials would keep passing.
    #
    # The values that matter are read at *import* time: ``langchain_tools._CORPUS``
    # is built when the module is first imported, during collection and before any
    # fixture runs. Hiding the file from a fixture would be too late to change what
    # it holds, which is why this is module-level code in the earliest conftest
    # rather than a fixture in the one next to the tests.
    #
    # Rebinds the module's path rather than patching ``Path.exists``, which
    # :func:`~tenantfirstaid.google_auth.load_gcp_credentials` also depends on.
    from tenantfirstaid import google_auth

    google_auth._ENV_PATH = Path("/nonexistent/backend/.env")
