import type { TChatMessage } from "../../../hooks/useMessages";
import DOMPurify, {
  SANITIZE_AI_SETTINGS,
} from "../../../shared/utils/dompurify";

interface Props {
  message: TChatMessage;
}

/**
 * Renders a single chat message bubble with sanitized HTML content.
 */
export default function MessageContent({ message }: Props) {
  const messageContent = DOMPurify.sanitize(
    message.text,
    SANITIZE_AI_SETTINGS,
  )
    .split("-----generate letter-----")[0]
    .trim();

  return (
    <>
      <strong>{message.type === "ai" ? "Bot: " : "You: "}</strong>
      <span className="whitespace-pre-wrap">
        {messageContent.length === 0 ? (
          <span className="animate-dot-pulse italic">Typing...</span>
        ) : (
          <span dangerouslySetInnerHTML={{ __html: messageContent }} />
        )}
      </span>
    </>
  );
}
