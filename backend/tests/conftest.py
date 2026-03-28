import pytest
from flask import Flask

from tenantfirstaid.location import OregonCity, UsaState


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
