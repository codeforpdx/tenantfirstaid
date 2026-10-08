import { deserializeAiMessage } from "../../../hooks/useMessages";
import type { ChatMessage, UiMessage } from "../../../shared/types/messages";
import {
  escapeHtml,
  stripAnchorTags,
} from "../../../shared/utils/sanitizeText";

const REDACTED_SPAN = `<span style="
        background-color: black;
        color:transparent;
        white-space: nowrap;
        user-select: none;
      ">${"_".repeat(10)}</span>`;

// Unicode-aware word boundary; a capture group instead of lookbehind keeps
// older Safari (< 16.4) working. The consumed delimiter means back-to-back
// matches like "C++C++" only redact the first.
const NON_WORD = "[^\\p{L}\\p{N}_]";

function buildRedactRegex(wordsToRedact: string): RegExp | null {
  const terms = wordsToRedact
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    // Longest first so a term that contains another redacts in full.
    .sort((a, b) => b.length - a.length)
    .map((s) =>
      s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+"),
    );
  if (terms.length === 0) return null;
  return new RegExp(
    `(^|${NON_WORD})(${terms.join("|")})(?=$|${NON_WORD})`,
    "giu",
  );
}

/**
 * Strips anchors, redacts matches in the raw text, then HTML-escapes everything between them.
 * Redacting before escaping keeps terms from matching entities or inserted markup.
 */
function redactAndEscape(text: string, regex: RegExp | null) {
  text = stripAnchorTags(text);
  if (regex === null) return escapeHtml(text);
  let result = "";
  let lastIndex = 0;
  for (const match of text.matchAll(regex)) {
    const start = match.index + match[1].length;
    result += escapeHtml(text.slice(lastIndex, start)) + REDACTED_SPAN;
    lastIndex = start + match[2].length;
  }
  return result + escapeHtml(text.slice(lastIndex));
}

/**
 * Submits user feedback along with a redacted chat transcript to the backend.
 * Builds an HTML transcript, applies word redaction, and sends via FormData.
 * Throws if there is no exchange to send, the request fails, or the server responds with an error.
 */
export default async function sendFeedback(
  messages: ChatMessage[],
  userFeedback: string,
  emailsToCC: string,
  wordsToRedact: string,
) {
  const transcriptMessages = messages.filter(
    (msg): msg is Exclude<ChatMessage, UiMessage> => msg.type !== "ui",
  );
  if (transcriptMessages.length < 2) {
    throw new Error("Not enough messages to send feedback");
  }

  const redactRegex = buildRedactRegex(wordsToRedact);
  const messageChain = transcriptMessages
    .map(
      (msg) =>
        `<p><strong>${
          msg.type === "human" ? "User" : "AI"
        }</strong>: ${redactAndEscape(msg.type === "ai" ? deserializeAiMessage(msg.text) : msg.text, redactRegex)}</p>`,
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

  const response = await fetch("/api/feedback", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Feedback request failed with status ${response.status}`);
  }
}
