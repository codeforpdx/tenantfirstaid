import sanitizeText from "../../../shared/utils/sanitizeText";


/**
 * Submits user feedback from the homepage- simple form to the backend.
 * Builds an HTML transcript, applies word redaction, and sends via FormData.
 */
export default async function sendHPFeedback(
  name: string,
  subject: string,
  feedback: string,
) {

  const htmlContent = `
    <html>
    <head>
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'none'; object-src 'none'; base-uri 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; form-action 'none';">
      <title>Feedback Form</title>
      <style>
        body {
          font-family: sans-serif;
        }
        strong {
          font-weight: bold;
        }
        p {
          margin: 6px 0;
          line-height: 1.2;
        }
      </style>
    </head>
    <body>
      ${feedback
        .split("\n")
        .map((line) => `<p>${sanitizeText(line)}</p>`)
        .join("")}
    </body>
    </html>
  `;

  const blob = new Blob([htmlContent], { type: "text/html" });
  const formData = new FormData();

  formData.append("name", name);
  formData.append("subject", subject);
  formData.append("feedback", feedback);
  formData.append("message", blob, "message.html");

  await fetch("/api/feedback", {
    method: "POST",
    body: formData,
  });
}
