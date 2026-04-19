from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from tenantfirstaid.location import OregonCity, UsaState


@pytest.fixture(autouse=True)
def _no_eval_history_writes(request):
    """Prevent tests from writing to the real eval_history directory.

    Skipped for test_eval_history.py, which tests those functions directly
    and manages its own HISTORY_DIR isolation via tmp_path patches.
    """
    if request.fspath.basename == "test_eval_history.py":
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
