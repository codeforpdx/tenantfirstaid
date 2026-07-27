"""User feedback handling: render the chat transcript to PDF and email it.

Backs the ``POST /api/feedback`` endpoint — see :func:`send_feedback`.
"""

import os
from io import BytesIO
from typing import Optional, Tuple

from flask import request
from flask_mailman import EmailMessage
from xhtml2pdf import pisa
from xhtml2pdf.context import pisaContext

MAX_ATTACHMENT_SIZE: int = 2 * 1024 * 1024
"""Maximum size in bytes for PDF attachments (2 MB)."""


def convert_html_to_pdf(html_content: str) -> Optional[bytes]:
    """Convert HTML content to a PDF byte string.

    Args:
        html_content: HTML markup to convert.

    Returns:
        PDF content as bytes, or None if conversion failed.
    """
    pdf_buffer = BytesIO()

    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    if isinstance(pisa_status, pisaContext) and pisa_status.err != 0:
        return None

    return pdf_buffer.getvalue()


def send_feedback() -> Tuple[str, int]:
    """Handle user feedback submission and email it with optional transcript PDF.

    Reads feedback form data from the request (feedback text, optional transcript HTML,
    optional name/subject for homepage feedback, and optional CC list). Converts the
    transcript to PDF if provided, validates file size, and sends an email.

    Returns:
        Tuple of (status_message, HTTP_status_code): (message, status_code). Returns
        200 on success, 413 for oversized attachments, or 500 on conversion/send errors.
    """
    feedback = request.form.get("feedback")
    file = request.files.get("transcript")

    emails_to_cc = request.form.get("emailsToCC")
    cc_list = []
    if emails_to_cc is not None:
        cc_list = [
            stripped_email
            for email in emails_to_cc.split(",")
            if (stripped_email := email.strip())
        ]

    if not file:
        name = request.form.get("name")
        subject = request.form.get("subject")
        email_params = {
            "subject": subject or "Homepage Feedback",
            "from_email": os.getenv("SENDER_EMAIL"),
            "to": [os.getenv("RECIPIENT_EMAIL")],
            "body": f"From: {name}\n\n{feedback}",
        }
        try:
            EmailMessage(**email_params).send()
            return "Message sent", 200
        except Exception as e:
            return f"Send failed: {str(e)}", 500

    html_content: str = file.read().decode("utf-8")
    pdf_content: Optional[bytes] = convert_html_to_pdf(html_content)
    if pdf_content is None:
        return "PDF conversion failed", 500

    if len(pdf_content) > MAX_ATTACHMENT_SIZE:
        return "Attachment too large", 413

    email_params = {
        "subject": "Feedback with Transcript",
        "from_email": os.getenv("SENDER_EMAIL"),
        "to": [os.getenv("RECIPIENT_EMAIL")],
        "body": f"User feedback:\n\n{feedback}\n\nTranscript is attached below",
        "cc": cc_list,
    }

    try:
        msg = EmailMessage(**email_params)
        msg.attach(
            "transcript.pdf",
            pdf_content,
            "application/pdf",
        )

        msg.send()
        return "Message sent", 200
    except Exception as e:
        return f"Send failed: {str(e)}", 500
