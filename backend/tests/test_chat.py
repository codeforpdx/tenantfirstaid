import pytest
import vertexai
from tenantfirstaid.chat import (
    ChatManager,
    DEFAULT_INSTRUCTIONS,
    OREGON_LAW_CENTER_PHONE_NUMBER,
)
from flask import Flask
from tenantfirstaid.chat import ChatView
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
)


@pytest.fixture
def mock_vertexai(mocker):
    mock_vertexai_init = mocker.Mock(spec=vertexai)
    mocker.patch("tenantfirstaid.chat.vertexai.init", return_value=mock_vertexai_init)
    return mock_vertexai_init


@pytest.fixture
def mock_vertexai_generative_model(mocker):
    mock_model = mocker.Mock(spec=GenerativeModel)
    mocker.patch("tenantfirstaid.chat.GenerativeModel", return_value=mock_model)
    return mock_model


@pytest.fixture
def chat_manager(mocker, mock_vertexai, mock_vertexai_generative_model):
    # Mock Google service account credentials
    mock_credentials = mocker.Mock()
    mocker.patch(
        "tenantfirstaid.chat.service_account.Credentials.from_service_account_file",
        return_value=mock_credentials,
    )
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
def app():
    app = Flask(__name__)
    app.testing = True  # propagate exceptions to the test client

    return app


def test_chat_view_dispatch_request_streams_response(
    app, mocker, mock_vertexai_generative_model
):
    """Test that sends a message to the API, mocks vertexai response, and validates output."""

    # Mock Google service account credentials
    mock_credentials = mocker.Mock()
    mocker.patch(
        "tenantfirstaid.chat.service_account.Credentials.from_service_account_file",
        return_value=mock_credentials,
    )

    # Mock the entire RAG module components to avoid actual RAG retrieval
    mock_rag_resource = mocker.Mock()
    mock_rag_store = mocker.Mock()
    mock_retrieval = mocker.Mock()
    mock_rag_tool = mocker.Mock(spec=Tool)

    mocker.patch("tenantfirstaid.chat.rag.RagResource", return_value=mock_rag_resource)
    mocker.patch("tenantfirstaid.chat.rag.VertexRagStore", return_value=mock_rag_store)
    mocker.patch("tenantfirstaid.chat.rag.Retrieval", return_value=mock_retrieval)
    mocker.patch("tenantfirstaid.chat.Tool.from_retrieval", return_value=mock_rag_tool)

    app.add_url_rule(
        "/api/query",
        view_func=ChatView.as_view("chat"),
        methods=["POST"],
    )

    # Mock the GenerativeModel's generate_content method
    mock_response_text = "This is a mocked response about tenant rights in Oregon. You should contact <a href='https://oregon.public.law/statutes/ORS_90.427' target='_blank'>ORS 90.427</a> for more information."

    # Create a mock response object that mimics the streaming response
    mock_candidate = mocker.Mock()
    mock_candidate.content.parts = [mocker.Mock()]
    mock_candidate.content.parts[0].text = mock_response_text

    mock_event = mocker.Mock()
    mock_event.candidates = [mock_candidate]

    # Mock the generate_content method to return our mock response as a stream
    mock_vertexai_generative_model.generate_content.return_value = iter([mock_event])

    # Send a message to the chat API
    test_message = "What are my rights as a tenant in Portland?"

    with app.test_request_context(
        "/api/query",
        method="POST",
        json={
            "messages": [{"role": "user", "content": test_message}],
            "city": "Portland",
            "state": "or",
        },
    ) as chat_ctx:
        # Execute the request
        chat_response = chat_ctx.app.full_dispatch_request()

        # Verify the response
        assert chat_response.status_code == 200
        assert chat_response.mimetype == "text/plain"

        # Get the response data by consuming the stream
        response_data = "".join(
            chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            for chunk in chat_response.response
        )
        assert response_data == mock_response_text

        # Verify that generate_content was called with correct parameters
        mock_vertexai_generative_model.generate_content.assert_called_once()
        call_args = mock_vertexai_generative_model.generate_content.call_args

        # Check that the user message was included in the call
        contents = call_args[1]["contents"]  # keyword arguments
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == test_message

        # Check that streaming was enabled
        assert call_args[1]["stream"] is True
