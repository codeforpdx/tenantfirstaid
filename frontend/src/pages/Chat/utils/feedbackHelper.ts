import type { IMessage } from "../../../hooks/useMessages";

function sanitizeText(str: string) {
  // Strips anchor tags
  str = str.replace(/<a\b[^>]*>(.*?)<\/a>/gi, "$1");

  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export default async function sendFeedback(
  messages: IMessage[],
  userFeedback: string,
) {
  if (messages.length < 2) return;

  const messageChain = messages
    .map(
      ({ role, content }) =>
        `<p><strong>${
          role.charAt(0).toUpperCase() + role.slice(1)
        }</strong>: ${sanitizeText(content)}</p>`,
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
  formData.append("transcript", blob, "transcript.html");

  await fetch("/api/feedback", {
    method: "POST",
    body: formData,
  });
}
