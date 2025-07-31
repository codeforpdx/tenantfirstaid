from xhtml2pdf import pisa
from io import BytesIO
from flask import request
from flask_mailman import EmailMessage
import os
from typing import Optional, Tuple

MAX_ATTACHMENT_SIZE: int = 2 * 1024 * 1024


def convert_html_to_pdf(html_content: str) -> Optional[bytes]:
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    if pisa_status.err:
        return None
    return pdf_buffer.getvalue()


def send_feedback() -> Tuple[str, int]:
    feedback = request.form.get("feedback")
    file = request.files.get("transcript")

    if not file:
        return "No file provided", 404

    html_content: str = file.read().decode("utf-8")
    pdf_content: Optional[bytes] = convert_html_to_pdf(html_content)
    if pdf_content is None:
        return "PDF conversion failed", 500

    if len(pdf_content) > MAX_ATTACHMENT_SIZE:
        return "Attachment too large", 413

    try:
        msg = EmailMessage(
            subject="Feedback with Transcript",
            from_email=os.getenv("SENDER_EMAIL"),
            to=[os.getenv("RECIPIENT_EMAIL")],
            body=f"User feedback:\n\n{feedback}\n\nTranscript is attached below",
        )
        msg.attach(
            "transcript.pdf",
            pdf_content,
            "application/pdf",
        )

        msg.send()
        return "Message sent", 200
    except Exception as e:
        return f"Send failed: {str(e)}", 500
