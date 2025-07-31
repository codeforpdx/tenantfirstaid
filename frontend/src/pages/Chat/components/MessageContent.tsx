import type { IMessage } from "../../../hooks/useMessages";

/* This was commented out because with new laws added (e.g. ORS Ch. 105)
 * and different municipal codes (e.g. Portland's code),
 * citation hightlighting was becoming too complex. We should revisit this
 * in the future, but for now the LLM returns links to the relevant statutes
 * and we use "dangerouslySetInnerHTML" to render them.
 * 
const orsRegex =
  /(?:ORS\s*)?\d{2,3}\.\d+[A-Za-z]?(?:\(\d+\)(?:\([a-zA-Z0-9]+\))*)?(?:[-&](?:ORS\s*)?\d{2,3}\.\d+[A-Za-z]?(?:\(\d+\)(?:\([a-zA-Z0-9]+\))*)?)?/g;

interface ORSProps {
  text: string;
  onStatuteClick: (statute: string) => void;
}

function HighlightORS({ text, onStatuteClick }: ORSProps) {
  const parts = [];
  const matches = Array.from(text.matchAll(orsRegex));
  let lastIndex = 0;

  matches.forEach((match) => {
    const index = match.index!;
    if (lastIndex < index) {
      parts.push(text.slice(lastIndex, index));
    }

    parts.push(
      <p
        key={index}
        className="inline text-blue-600 underline cursor-pointer transition-colors hover:bg-blue-200 rounded"
        onClick={() => onStatuteClick(match[0])}
      >
        {match[0]}
      </p>,
    );

    lastIndex = index + match[0].length;
  });

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
}
*/

interface Props {
  message: IMessage;
  isLoading: boolean;
  onStatuteClick: (statute: string) => void;
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
          dangerouslySetInnerHTML={{ __html: message.content }}
        ></span>
      )}
    </>
  );
}
