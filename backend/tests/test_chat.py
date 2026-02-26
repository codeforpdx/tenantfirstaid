import pytest
from flask import Flask
from langchain_core.messages.content import create_text_block

from tenantfirstaid.chat import ChatView, _classify_blocks
from tenantfirstaid.langchain_chat_manager import LangChainChatManager


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def reasoning_block(reasoning: str) -> dict:
    return {"type": "reasoning", "reasoning": reasoning}


def chunks(blocks):
    return list(_classify_blocks(iter(blocks)))


class TestClassifyBlocks:
    def test_plain_text_passthrough(self):
        result = chunks([text_block("Here is some advice.")])
        assert len(result) == 1
        assert result[0].type == "text"
        assert result[0].text == "Here is some advice."

    def test_reasoning_passthrough(self):
        result = chunks([reasoning_block("Let me think.")])
        assert len(result) == 1
        assert result[0].type == "reasoning"
        assert result[0].reasoning == "Let me think."

    def test_letter_passthrough(self):
        result = chunks([{"type": "letter", "letter": "Dear Landlord,"}])
        assert len(result) == 1
        assert result[0].type == "letter"
        assert result[0].letter == "Dear Landlord,"


@pytest.fixture
def chat_manager(mocker):
    m = mocker.patch.object(LangChainChatManager, "agent", spec=True)
    yield m


@pytest.fixture
def app():
    app = Flask(__name__)
    app.testing = True  # propagate exceptions to the test client

    return app


@pytest.mark.skip("work-in-progress")
def test_chat_view_dispatch_request_streams_response(app, mocker, chat_manager):
    """Test that sends a message to the API, mocks vertexai response, and validates output."""

    app.add_url_rule(
        "/api/query",
        view_func=ChatView.as_view("chat"),
        methods=["POST"],
    )

    # Mock the GenerativeModel's generate_content method
    mock_response_text = "This is a mocked response about tenant rights in Oregon. You should contact <a href='https://oregon.public.law/statutes/ORS_90.427' target='_blank'>ORS 90.427</a> for more information."
    mock_event = create_text_block(mock_response_text)

    # Mock the generate_content method to return our mock response as a stream
    # FIXME: this is not really mocking!!!
    chat_manager.agent.stream.return_value = iter([mock_event])

    # Send a message to the chat API
    test_message = "What are my rights as a tenant in Portland?"

    with app.test_request_context(
        "/api/query",
        method="POST",
        json={
            "messages": [{"role": "human", "content": test_message}],
            "city": "Portland",
            "state": "or",
            "thread_id": "some-thread-id",
        },
    ) as chat_ctx:
        # Execute the request
        chat_response = chat_ctx.app.full_dispatch_request()

        # Verify the response
        assert chat_response.status_code == 200
        assert chat_response.mimetype == "text/plain"

        # Get the response data by consuming the stream
        _response_data = "".join(
            chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            for chunk in chat_response.response
        )
        # assert response_data == mock_response_text

        # # Verify that generate_content was called with correct parameters
        # mock_vertexai_client.models.generate_content_stream.assert_called_once()
        # call_args = mock_vertexai_client.models.generate_content_stream.call_args

        # # Check that the user message was included in the call
        # contents = call_args[1]["contents"]  # keyword arguments
        # assert len(contents) == 1
        # assert contents[0]["role"] == "user"
        # assert contents[0]["parts"][0]["text"] == test_message
