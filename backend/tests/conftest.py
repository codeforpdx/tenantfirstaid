from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Imported for side effects: the autouse fixture below patches attributes on
# these submodules by string path, which requires them to be importable as
# attributes of the `evaluate` package.
import evaluate.measure_evaluator_variance  # noqa: F401
import evaluate.run_langsmith_evaluation  # noqa: F401
from tenantfirstaid.location import OregonCity, UsaState


@pytest.fixture(autouse=True)
def _no_langsmith_tracing(monkeypatch: pytest.MonkeyPatch):
    """Keep the suite from shipping spans to the hosted LangSmith project.

    The tests exercise real LangChain/LangGraph objects, so with a live
    LANGSMITH_API_KEY present every run uploads hundreds of spans - polluting the
    real traces and consuming the tenant's monthly trace quota. Exporting the
    variable outside pytest is not enough on its own: backend/.env is loaded with
    override=True inside _GoogEnvAndPolicy.__init__, which production code runs
    exactly once, at import time, when tenantfirstaid.constants builds its
    SINGLETON. So whether an exported value survives depends on when that module
    is first imported relative to the exporter. Re-asserting the variables here
    per test makes the guarantee independent of import ordering and of any future
    code path that constructs a second config object.

    LANGSMITH_API_KEY is deleted alongside them as belt-and-braces: with no key in
    the environment the LangSmith client cannot authenticate even if some code
    path re-enables tracing. A test that needs the key sets it itself, and its own
    monkeypatch wins inside its body.
    """
    for var in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.setenv(var, "false")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)


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
