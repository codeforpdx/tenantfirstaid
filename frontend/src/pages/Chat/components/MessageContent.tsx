import type { IMessage } from "../../../hooks/useMessages";
import DOMPurify, { SANITIZE_SETTINGS } from "../../../shared/utils/dompurify";

interface Props {
  message: IMessage;
  isLoading: boolean;
}

export default function MessageContent({ message, isLoading }: Props) {
  return (
    <>
      <strong>{message.role === "model" ? "Bot: " : "You: "}</strong>
      {message.role === "model" && message.content === "" && isLoading ? (
        <span className="animate-dot-pulse">...</span>
      ) : (
        <span
          className="whitespace-pre-wrap"
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(message.content, SANITIZE_SETTINGS)
              .split("-----generate letter-----")[0]
              .trim(),
          }}
        ></span>
      )}
    </>
  );
}
