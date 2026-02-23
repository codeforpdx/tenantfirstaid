import SafeMarkdown from "../../../shared/components/SafeMarkdown";
import type { TChatMessage } from "../../../hooks/useMessages";
import type { TResponseChunk } from "../../../types/MessageTypes";

interface ChunkProps {
  chunkObj: TResponseChunk;
}

function RenderedChunk({ chunkObj }: ChunkProps) {
  switch (chunkObj.type) {
    case "text":
      return <SafeMarkdown>{chunkObj.text}</SafeMarkdown>;
    case "reasoning":
      return (
        <div className="flex gap-2 my-2">
          {/* reasoning chunk */}
          {`\u{1F914}`}
          <span className="italic text-slate-500 leading-relaxed">
            {chunkObj.reasoning}
          </span>
        </div>
      );
    default:
      return null;
  }
}

interface Props {
  message: TChatMessage;
}

/**
 * Renders a single chat message bubble.
 * AI messages are parsed as newline-delimited JSON chunks and rendered as markdown.
 * Human messages are rendered as plain markdown.
 */
export default function MessageContent({ message }: Props) {
  return (
    <>
      <strong>{message.type === "ai" ? "Bot: " : "You: "}</strong>
      <div>
        {message.text.length === 0 ? (
          <span className="animate-dot-pulse italic">Typing...</span>
        ) : (
          <>
            {message.type === "ai" ? (
              <>
                {message.text
                  .split("\n")
                  .filter((chunk) => chunk.length !== 0)
                  .map((chunk, index) => {
                    try {
                      const chunkObj = JSON.parse(chunk) as TResponseChunk;
                      return (
                        <RenderedChunk
                          key={chunkObj.type + index}
                          chunkObj={chunkObj}
                        />
                      );
                    } catch {
                      return (
                        <SafeMarkdown key={`automated-${index}`}>
                          {chunk}
                        </SafeMarkdown>
                      );
                    }
                  })}
              </>
            ) : (
              <SafeMarkdown>{message.text}</SafeMarkdown>
            )}
          </>
        )}
      </div>
    </>
  );
}
