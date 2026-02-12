import type { IChatMessage } from "../../../hooks/useMessages";
import sanitizeText from "../../../shared/utils/sanitizeText";

/**
 * Opens a printable window with the conversation history.
 * Sanitizes message content before rendering to prevent XSS.
 */
export default function exportMessages(messages: IChatMessage[]) {
  if (messages.length < 2) return;

  const newDocument = window.open("", "", "height=800,width=600");
  const messageChain = messages
    .map(
      ({ role, content }) =>
        `<p><strong>${
          role === "human" ? "User" : "AI"
        }</strong>: ${sanitizeText(content)}</p>`,
    )
    .join("");

  newDocument?.document.writeln(`
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
  `);

  newDocument?.document.close();
  newDocument?.focus();
  newDocument?.print();
}
