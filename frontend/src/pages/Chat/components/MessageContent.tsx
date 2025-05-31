import type { IMessage } from "../../../hooks/useMessages";

const orsRegex =
  /(?:ORS\s*)?\d{2,3}\.\d+[A-Za-z]?(?:\(\d+\)(?:\([a-zA-Z0-9]+\))*)?(?:[-&](?:ORS\s*)?\d{2,3}\.\d+[A-Za-z]?(?:\(\d+\)(?:\([a-zA-Z0-9]+\))*)?)?/g;

interface ORSProps {
  text: string;
}

function HighlightORS({ text }: ORSProps) {
  const parts = [];
  const matches = Array.from(text.matchAll(orsRegex));
  let lastIndex = 0;

  matches.forEach((match) => {
    const index = match.index!;
    if (lastIndex < index) {
      parts.push(text.slice(lastIndex, index));
    }
    const baseStatuteMatch = match[0].match(/(?:ORS\s*)?(\d{2,3}\.\d+)/);
    const baseStatute = baseStatuteMatch ? baseStatuteMatch[1] : "";

    parts.push(
      <a
        key={index}
        className="text-blue-600 underline cursor-pointer"
        onClick={() => {
          console.log(match[0]);
        }}
        href={`https://oregon.public.law/statutes/ors_${baseStatute}`}
        target="_blank"
      >
        {match[0]}
      </a>
    );

    lastIndex = index + match[0].length;
  });

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
}

interface Props {
  message: IMessage;
  isLoading: boolean;
}

export default function MessageContent({ message, isLoading }: Props) {
  return (
    <>
      <strong>{message.role === "assistant" ? "Bot: " : "You: "}</strong>
      {message.role === "assistant" && message.content === "" && isLoading ? (
        <span className="animate-dot-pulse">...</span>
      ) : (
        <span className="whitespace-pre-wrap">
          <HighlightORS text={message.content} />
        </span>
      )}
    </>
  );
}
