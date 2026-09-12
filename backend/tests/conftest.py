from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Imported for side effects: the autouse fixture below patches attributes on
# these submodules by string path, which requires them to be importable as
# attributes of the `evaluate` package.
import evaluate.measure_evaluator_variance  # noqa: F401
import evaluate.run_langsmith_evaluation  # noqa: F401
import evaluate.langsmith_dataset  # noqa: F401
from tenantfirstaid.location import OregonCity, UsaState


@pytest.fixture(autouse=True)
def _no_langsmith_tracing(monkeypatch: pytest.MonkeyPatch, mocker):
    """Keep the suite from shipping spans to the hosted LangSmith project.

    Tracing is disabled by patching `tracing_is_enabled` directly because
    `get_env_var` is lru_cached and `tracing_is_enabled()` checks
    `LANGCHAIN_TRACING_V2` before `LANGSMITH_TRACING`. The env vars are kept
    as cheap defense-in-depth, not the actual guarantee.

    `LANGSMITH_API_KEY` is bound at import time into three consuming modules,
    so `delenv` alone cannot protect a real `Client()` construction there;
    the fixture patches each module's own binding instead, following the
    pattern in `test_langsmith_dataset.py`.

    A test that wants real tracing back on will need to override this
    fixture's `tracing_is_enabled` patch itself, not just set env vars.
    """
    for var in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.setenv(var, "false")
    mocker.patch("langsmith.utils.tracing_is_enabled", return_value=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    mocker.patch("evaluate.langsmith_dataset.LANGSMITH_API_KEY", None)
    mocker.patch("evaluate.run_langsmith_evaluation.LANGSMITH_API_KEY", None)
    mocker.patch("evaluate.measure_evaluator_variance.LANGSMITH_API_KEY", None)


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
