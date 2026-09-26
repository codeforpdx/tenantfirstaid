from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import evaluate.langsmith_dataset  # noqa: F401

# Imported for side effects: the autouse fixture below patches attributes on
# these submodules by string path, which requires them to be importable as
# attributes of the `evaluate` package.
import evaluate.measure_evaluator_variance  # noqa: F401
import evaluate.run_langsmith_evaluation  # noqa: F401
from evaluate.tracing import LangsmithConfig
from tenantfirstaid.google_auth import GcpEnvironment, load_env_file
from tenantfirstaid.location import OregonCity, UsaState


@pytest.fixture(autouse=True)
def _no_langsmith_tracing(monkeypatch: pytest.MonkeyPatch, mocker):
    """Keep the suite from shipping spans to the hosted LangSmith project.

    Tracing is disabled by patching `tracing_is_enabled` directly because
    `get_env_var` is lru_cached and `tracing_is_enabled()` checks
    `LANGCHAIN_TRACING_V2` before `LANGSMITH_TRACING`. The env vars are kept
    as cheap defense-in-depth, not the actual guarantee.

    `delenv` alone cannot protect a real `Client()` construction, because
    `LangsmithConfig.from_env()` reloads `.env` over the ambient environment; the
    fixture substitutes the reader itself. One patch covers every caller, since they
    reach it through the `tracing` module rather than binding its result.

    A test that wants real tracing back on will need to override this
    fixture's `tracing_is_enabled` patch itself, not just set env vars.
    """
    for var in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.setenv(var, "false")
    mocker.patch("langsmith.utils.tracing_is_enabled", return_value=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    mocker.patch(
        "evaluate.tracing.LangsmithConfig.from_env",
        return_value=LangsmithConfig(api_key=None),
    )


@pytest.fixture(autouse=True)
def _no_real_gcp_credentials(mocker):
    """Keep the suite from loading real credentials off the machine it runs on.

    `RagBuilder` loads credentials while constructing, through
    `GcpEnvironment.load_credentials()`. On a developer machine `.env` points
    `GOOGLE_APPLICATION_CREDENTIALS` at a real file, so that succeeds and the test
    passes; CI has no `.env` and points the variable at a path that deliberately
    does not exist, so the same test fails there. Substituting the loader makes the
    suite behave identically either way, and keeps a unit test from depending on
    whether whoever ran it has authenticated.

    Tests of the loader itself call `load_gcp_credentials` directly, which this
    does not touch.
    """
    mocker.patch.object(GcpEnvironment, "load_credentials", return_value=MagicMock())


@pytest.fixture(autouse=True)
def _no_eval_history_writes(request: pytest.FixtureRequest):
    """Prevent tests from writing to the real eval_history directory."""
    if request.node.get_closest_marker("allow_eval_history_writes"):
        yield
        return
    with (
        patch(
            "evaluate.run_langsmith_evaluation.write_run_entry",
            return_value=MagicMock(spec=Path),
        ),
        patch(
            "evaluate.measure_evaluator_variance.write_variance_entry",
            return_value=MagicMock(spec=Path),
        ),
    ):
        yield


@pytest.fixture
def oregon_state():
    return UsaState.from_maybe_str("or")


@pytest.fixture
def portland_city():
    return OregonCity.from_maybe_str("Portland")


@pytest.fixture
def eugene_city():
    return OregonCity.from_maybe_str("Eugene")


@pytest.fixture
def app():
    """Flask app with testing=True for use in test client and request context."""
    app = Flask(__name__)
    app.testing = True
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def mock_chat_manager(mocker):
    """Mocked LangChainChatManager that yields canned streaming responses."""
    mock = mocker.patch("tenantfirstaid.chat.LangChainChatManager", autospec=True)
    instance = mock.return_value
    instance.generate_streaming_response.return_value = iter(
        [{"type": "text", "text": "Mocked legal advice."}]
    )
    return instance


@pytest.fixture(autouse=True)
def _fresh_env_file_snapshot():
    """Reset the one-time ``.env`` snapshot between tests.

    :func:`~tenantfirstaid.google_auth.load_env_file` is cached so a process reads
    the file once. Tests need the opposite -- one that patches the file away must
    not be decided by whether an earlier test already loaded it.
    """
    load_env_file.cache_clear()
    yield
    load_env_file.cache_clear()
