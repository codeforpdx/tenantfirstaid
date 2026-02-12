import type { IChatMessage } from "../../../hooks/useMessages";
import sanitizeText from "../../../shared/utils/sanitizeText";

function redactText(message: string, wordsToRedact: string) {
  let redactedMessage = message;
  const redactList = wordsToRedact
    .split(/\s*,\s*/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  redactList.forEach((word) => {
    const regex = new RegExp(`\\b${word.replace(/\s+/g, "\\s+")}\\b`, "gi");
    redactedMessage = redactedMessage.replace(regex, () => {
      return `<span style="
        background-color: black;
        color:transparent;
        white-space: nowrap;
        user-select: none;
      ">${"_".repeat(10)}</span>`;
    });
  });
  return redactedMessage;
}

/**
 * Submits user feedback along with a redacted chat transcript to the backend.
 * Builds an HTML transcript, applies word redaction, and sends via FormData.
 */
export default async function sendFeedback(
  messages: IChatMessage[],
  userFeedback: string,
  emailsToCC: string,
  wordsToRedact: string,
) {
  if (messages.length < 2) return;

  const messageChain = messages
    .map(
      ({ role, content }) =>
        `<p><strong>${
          role === "human" ? "User" : "AI"
        }</strong>: ${redactText(sanitizeText(content), wordsToRedact)}</p>`,
    )
    .join("");

  const htmlContent = `
    <html>
    <head>
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'none'; object-src 'none'; base-uri 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; form-action 'none';">
      <title>Conversation History</title>
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
      ${messageChain}
    </body>
    </html>
  `;

  const blob = new Blob([htmlContent], { type: "text/html" });
  const formData = new FormData();

  formData.append("feedback", userFeedback);
  formData.append("emailsToCC", emailsToCC);
  formData.append("transcript", blob, "transcript.html");

  await fetch("/api/feedback", {
    method: "POST",
    body: formData,
  });
}
