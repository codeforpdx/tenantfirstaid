"""Tests for Flask app routes, CORS, and rate limiting."""

from unittest.mock import patch

import pytest

from tenantfirstaid.app import app, limiter


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter between tests."""
    limiter.reset()
    yield


class TestCors:
    @patch("tenantfirstaid.chat.LangChainChatManager")
    def test_allowed_origin_gets_cors_headers(self, mock_cm_cls, client):
        mock_cm_cls.return_value.generate_streaming_response.return_value = iter(
            [{"type": "text", "text": "ok"}]
        )
        resp = client.post(
            "/api/query",
            json={"messages": [], "city": None, "state": "or"},
            headers={"Origin": "https://tenantfirstaid.com"},
        )
        assert (
            resp.headers.get("Access-Control-Allow-Origin")
            == "https://tenantfirstaid.com"
        )

    @patch("tenantfirstaid.chat.LangChainChatManager")
    def test_disallowed_origin_no_cors_headers(self, mock_cm_cls, client):
        mock_cm_cls.return_value.generate_streaming_response.return_value = iter(
            [{"type": "text", "text": "ok"}]
        )
        resp = client.post(
            "/api/query",
            json={"messages": [], "city": None, "state": "or"},
            headers={"Origin": "https://evil.com"},
        )
        assert "Access-Control-Allow-Origin" not in resp.headers


class TestQueryRoute:
    @patch("tenantfirstaid.chat.LangChainChatManager")
    def test_post_query_returns_200(self, mock_cm_cls, client):
        mock_cm_cls.return_value.generate_streaming_response.return_value = iter(
            [{"type": "text", "text": "Hello"}]
        )
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

    def test_get_query_returns_405(self, client):
        resp = client.get("/api/query")
        assert resp.status_code == 405

    def test_unknown_route_returns_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404


class TestFeedbackRoute:
    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_post_feedback_returns_200(self, mock_email_cls, client):
        resp = client.post(
            "/api/feedback",
            data={"name": "Jane", "subject": "Bug", "feedback": "Broken"},
        )
        assert resp.status_code == 200

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_rate_limiting_returns_429(self, mock_email_cls, client):
        for _ in range(3):
            client.post(
                "/api/feedback",
                data={"name": "Jane", "subject": "Bug", "feedback": "Broken"},
            )
        resp = client.post(
            "/api/feedback",
            data={"name": "Jane", "subject": "Bug", "feedback": "Broken"},
        )
        assert resp.status_code == 429


class TestContentType:
    @patch("tenantfirstaid.chat.LangChainChatManager")
    def test_streaming_response_content_type(self, mock_cm_cls, client):
        mock_cm_cls.return_value.generate_streaming_response.return_value = iter(
            [{"type": "text", "text": "Hi"}]
        )
        resp = client.post(
            "/api/query",
            json={
                "messages": [{"role": "human", "content": "Hello"}],
                "city": None,
                "state": "or",
            },
        )
        assert resp.mimetype == "text/plain"
