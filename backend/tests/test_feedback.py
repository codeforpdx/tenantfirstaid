"""Tests for feedback email and PDF conversion."""

import io
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from xhtml2pdf.context import pisaContext

from tenantfirstaid.feedback import convert_html_to_pdf, send_feedback


@pytest.fixture
def feedback_app():
    """Flask app configured for feedback testing."""
    app = Flask(__name__)
    app.testing = True
    app.config["MAIL_SERVER"] = "smtp.test.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = "test@test.com"
    app.config["MAIL_PASSWORD"] = "password"
    app.config["MAIL_DEFAULT_SENDER"] = "test@test.com"
    return app


class TestConvertHtmlToPdf:
    @patch("tenantfirstaid.feedback.pisa")
    def test_valid_html_returns_bytes(self, mock_pisa):
        mock_status = MagicMock()
        mock_status.err = 0
        mock_pisa.CreatePDF.return_value = mock_status

        result = convert_html_to_pdf("<html><body>Hello</body></html>")
        assert isinstance(result, bytes)

    @patch("tenantfirstaid.feedback.pisa")
    def test_pisa_error_returns_none(self, mock_pisa):
        mock_status = MagicMock(spec=pisaContext)
        mock_status.err = 1
        mock_pisa.CreatePDF.return_value = mock_status

        result = convert_html_to_pdf("<html><body>Bad</body></html>")
        assert result is None


class TestSendFeedbackSimple:
    """Tests for feedback without transcript attachment."""

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_simple_feedback_sends_email(self, mock_email_cls, feedback_app):
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"name": "Jane", "subject": "Bug", "feedback": "Broken page"},
        ):
            msg, status = send_feedback()
        assert status == 200
        assert msg == "Message sent"
        mock_email_cls.return_value.send.assert_called_once()

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_simple_feedback_without_subject_uses_default(
        self, mock_email_cls, feedback_app
    ):
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"name": "Jane", "feedback": "Broken page"},
        ):
            msg, status = send_feedback()
        assert status == 200
        call_kwargs = mock_email_cls.call_args[1]
        assert call_kwargs["subject"] == "Homepage Feedback"

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_email_failure_returns_500(self, mock_email_cls, feedback_app):
        mock_email_cls.return_value.send.side_effect = Exception("SMTP down")
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"name": "Jane", "subject": "Bug", "feedback": "Help"},
        ):
            msg, status = send_feedback()
        assert status == 500
        assert "SMTP down" in msg


class TestSendFeedbackWithTranscript:
    """Tests for feedback with transcript file attached."""

    def _make_file(self, content: str = "<html><body>Chat log</body></html>"):
        return (io.BytesIO(content.encode("utf-8")), "transcript.html")

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch("tenantfirstaid.feedback.convert_html_to_pdf", return_value=b"%PDF-fake")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_transcript_happy_path(self, mock_pdf, mock_email_cls, feedback_app):
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"feedback": "Great chat", "transcript": self._make_file()},
            content_type="multipart/form-data",
        ):
            msg, status = send_feedback()
        assert status == 200
        mock_email_cls.return_value.attach.assert_called_once()

    @patch("tenantfirstaid.feedback.convert_html_to_pdf", return_value=None)
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_pdf_conversion_failure_returns_500(self, mock_pdf, feedback_app):
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"feedback": "Chat", "transcript": self._make_file()},
            content_type="multipart/form-data",
        ):
            msg, status = send_feedback()
        assert status == 500
        assert "PDF" in msg

    @patch("tenantfirstaid.feedback.convert_html_to_pdf")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_oversized_attachment_returns_413(self, mock_pdf, feedback_app):
        mock_pdf.return_value = b"x" * (2 * 1024 * 1024 + 1)
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"feedback": "Chat", "transcript": self._make_file()},
            content_type="multipart/form-data",
        ):
            msg, status = send_feedback()
        assert status == 413
        assert "large" in msg.lower()

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch("tenantfirstaid.feedback.convert_html_to_pdf", return_value=b"%PDF-fake")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_cc_recipients_parsed(self, mock_pdf, mock_email_cls, feedback_app):
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={
                "feedback": "Chat",
                "transcript": self._make_file(),
                "emailsToCC": "a@b.com, c@d.com",
            },
            content_type="multipart/form-data",
        ):
            msg, status = send_feedback()
        assert status == 200
        call_kwargs = mock_email_cls.call_args[1]
        assert call_kwargs["cc"] == ["a@b.com", "c@d.com"]

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch("tenantfirstaid.feedback.convert_html_to_pdf", return_value=b"%PDF-fake")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_cc_empty_strings_filtered(self, mock_pdf, mock_email_cls, feedback_app):
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={
                "feedback": "Chat",
                "transcript": self._make_file(),
                "emailsToCC": "a@b.com, , ,c@d.com",
            },
            content_type="multipart/form-data",
        ):
            msg, status = send_feedback()
        assert status == 200
        call_kwargs = mock_email_cls.call_args[1]
        assert call_kwargs["cc"] == ["a@b.com", "c@d.com"]

    @patch("tenantfirstaid.feedback.EmailMessage")
    @patch("tenantfirstaid.feedback.convert_html_to_pdf", return_value=b"%PDF-fake")
    @patch.dict("os.environ", {"SENDER_EMAIL": "s@t.com", "RECIPIENT_EMAIL": "r@t.com"})
    def test_email_failure_with_transcript_returns_500(
        self, mock_pdf, mock_email_cls, feedback_app
    ):
        mock_email_cls.return_value.send.side_effect = Exception("Connection refused")
        with feedback_app.test_request_context(
            "/api/feedback",
            method="POST",
            data={"feedback": "Chat", "transcript": self._make_file()},
            content_type="multipart/form-data",
        ):
            msg, status = send_feedback()
        assert status == 500
        assert "Connection refused" in msg
