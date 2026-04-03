from langchain_core.messages import NonStandardContentBlock

from tenantfirstaid.chat import ChatView, _classify_blocks


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def reasoning_block(reasoning: str) -> dict:
    return {"type": "reasoning", "reasoning": reasoning}


def letter_block(content: str) -> NonStandardContentBlock:
    return NonStandardContentBlock(
        type="non_standard", value={"type": "letter", "content": content}
    )


def chunks(blocks):
    return list(_classify_blocks(iter(blocks)))


class TestClassifyBlocks:
    def test_plain_text_passthrough(self):
        result = chunks([text_block("Here is some advice.")])
        assert len(result) == 1
        assert result[0].type == "text"
        assert result[0].content == "Here is some advice."

    def test_reasoning_passthrough(self):
        result = chunks([reasoning_block("Let me think.")])
        assert len(result) == 1
        assert result[0].type == "reasoning"
        assert result[0].content == "Let me think."

    def test_letter_passthrough(self):
        result = chunks([letter_block("Dear Landlord,")])
        assert len(result) == 1
        assert result[0].type == "letter"
        assert result[0].content == "Dear Landlord,"

    def test_unknown_block_type_is_skipped(self, app):
        with app.app_context():
            result = chunks([{"type": "image", "image": "..."}])
        assert result == []

    def test_empty_content_text(self):
        result = chunks([text_block("")])
        assert len(result) == 1
        assert result[0].content == ""

    def test_mixed_block_stream(self, app):
        blocks = [
            text_block("Hello"),
            reasoning_block("Thinking..."),
            letter_block("Dear Landlord,"),
            {"type": "unknown_widget", "data": "???"},
        ]
        with app.app_context():
            result = chunks(blocks)
        assert len(result) == 3
        assert result[0].type == "text"
        assert result[1].type == "reasoning"
        assert result[2].type == "letter"


class TestDispatchRequest:
    def test_happy_path_streams_ndjson(self, app, mock_chat_manager):
        app.add_url_rule(
            "/api/query", view_func=ChatView.as_view("chat"), methods=["POST"]
        )

        with app.test_client() as client:
            resp = client.post(
                "/api/query",
                json={
                    "messages": [{"role": "human", "content": "Help me"}],
                    "city": "Portland",
                    "state": "or",
                },
            )
        assert resp.status_code == 200
        assert resp.mimetype == "text/plain"
        lines = resp.data.decode().strip().split("\n")
        assert len(lines) >= 1
