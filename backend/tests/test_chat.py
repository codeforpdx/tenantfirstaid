import pytest
import vertexai
from tenantfirstaid.chat import (
    ChatManager,
    DEFAULT_INSTRUCTIONS,
    OREGON_LAW_CENTER_PHONE_NUMBER,
)
from flask import Flask
from tenantfirstaid.chat import ChatView
from tenantfirstaid.session import TenantSession, TenantSessionData, InitSessionView
from vertexai.generative_models import (
    GenerationConfig,
    GenerationResponse,
    GenerativeModel,
)
from typing import Dict


@pytest.fixture
def mock_vertexai(mocker):
    mock_vertexai_init = mocker.Mock(spec=vertexai)
    mocker.patch("tenantfirstaid.chat.vertexai", return_value=mock_vertexai_init)
    return mock_vertexai_init


@pytest.fixture
def mock_vertexai_generative_model(mocker):
    mock_model = mocker.Mock(spec=GenerativeModel)
    mocker.patch("tenantfirstaid.chat.GenerativeModel", return_value=mock_model)
    return mock_model


@pytest.fixture
def mock_vertexai_generation_config(mocker):
    mock_gen_config = mocker.Mock(spec=GenerationConfig)
    mocker.patch("tenantfirstaid.chat.GenerationConfig", return_value=mock_gen_config)
    return mock_gen_config


@pytest.fixture
def chat_manager(mocker, mock_vertexai):
    return ChatManager()


def test_prepare_developer_instructions_includes_city_state(chat_manager):
    city = "Portland"
    state = "or"
    instructions = chat_manager.prepare_developer_instructions(city, state)
    assert f"The user is in {city} {state.upper()}." in instructions


def test_default_instructions_contains_oregon_law_center_phone():
    assert OREGON_LAW_CENTER_PHONE_NUMBER in DEFAULT_INSTRUCTIONS


def test_default_instructions_contains_citation_links():
    assert "https://oregon.public.law/statutes" in DEFAULT_INSTRUCTIONS
    assert 'target="_blank"' in DEFAULT_INSTRUCTIONS


@pytest.fixture
def mock_valkey_ping_nop(mocker, monkeypatch):
    """Mock the Valkey class with the db_con.ping() method."""

    monkeypatch.setenv("DB_HOST", "8.8.8.8")
    monkeypatch.setenv("DB_PORT", "8888")
    monkeypatch.setenv("DB_PASSWORD", "test_password")
    monkeypatch.setenv("DB_USE_SSL", "false")

    mock_valkey_client = mocker.Mock()
    mocker.patch("tenantfirstaid.session.Valkey", return_value=mock_valkey_client)
    mock_valkey_client.ping = ()
    return mock_valkey_client


@pytest.fixture
def mock_valkey(mock_valkey_ping_nop, mocker):
    _data: Dict[str, str] = {}

    mock_valkey_ping_nop.set = mocker.Mock(
        side_effect=lambda key, value: _data.update({key: value})
    )

    mock_valkey_ping_nop.get = mocker.Mock(side_effect=lambda key: _data[key])

    return mock_valkey_ping_nop


@pytest.fixture
def app(mock_valkey):
    app = Flask(__name__)
    app.testing = True  # propagate exceptions to the test client
    app.secret_key = "test_secret_key"  # Set a secret key for session management

    return app


def test_chat_view_dispatch_request_streams_response(
    app, mocker, mock_vertexai_generative_model
):
    tenant_session = TenantSession()

    app.add_url_rule(
        "/api/init",
        view_func=InitSessionView.as_view("init", tenant_session),
        methods=["POST"],
    )

    app.add_url_rule(
        "/api/query",
        view_func=ChatView.as_view("chat", tenant_session),
        methods=["POST"],
    )

    test_data_obj = TenantSessionData(
        city="Test City",
        state="Test State",
        messages=[],
    )

    # Initialize the session with session_id and test data
    with app.test_request_context(
        "/api/init", method="POST", json=test_data_obj
    ) as init_ctx:
        init_response = app.full_dispatch_request()
        assert init_response.status_code == 200  # Ensure the response is successful

        tenant_session.set(test_data_obj)
        session_id = init_response.json["session_id"]
        assert session_id is not None  # Ensure session_id is set
        assert isinstance(session_id, str)  # Ensure session_id is a string
        assert tenant_session.get() == test_data_obj

    # each test-request is a new context (nesting does not do what you think)
    # so we need to set the session_id in the request context manually
    with app.test_request_context(
        "/api/query", method="POST", json={"message": "Salutations mock openai api"}
    ) as chat_ctx:
        chat_ctx.session["session_id"] = (
            session_id  # Simulate session ID in request context
        )
        chat_response = init_ctx.app.full_dispatch_request()
        assert chat_response.status_code == 200  # Ensure the response is successful
        assert chat_response.mimetype == "text/plain"

        mock_vertexai_generative_model.generate_content = mocker.Mock(
            return_value=iter(
                [
                    GenerationResponse.from_dict(
                        response_dict=dict(
                            candidates=[
                                dict(
                                    content=dict(
                                        role="model",
                                        parts=[dict(text="Greetings, test prompt!")],
                                    )
                                )
                            ]
                        )
                    )
                ]
            )
        )

        response_chunks = "".join(chat_response.response)
        assert "Greetings, test prompt!" in response_chunks
