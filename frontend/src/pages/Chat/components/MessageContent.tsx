import clsx from "clsx";
import type { IMessage } from "../../../hooks/useMessages";
import DOMPurify, {
  SANITIZE_AI_SETTINGS,
} from "../../../shared/utils/dompurify";

interface Props {
  message: IMessage;
}

export default function MessageContent({ message }: Props) {
  const messageContent = DOMPurify.sanitize(
    message.content,
    SANITIZE_AI_SETTINGS,
  )
    .split("-----generate letter-----")[0]
    .trim();

  return (
    <>
      <strong>{message.role === "ai" ? "Bot: " : "You: "}</strong>
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
