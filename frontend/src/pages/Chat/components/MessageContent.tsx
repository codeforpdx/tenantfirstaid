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
          {/* reasoning chunk is styled to help differentiate reasoning from text */}
          {`\u{1F914}`}
          <em className="text-slate-500 leading-relaxed">
            {chunkObj.reasoning}
          </em>
        </div>
      );
    // No letter case (chunk handled in letter panel)
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
  if (message.type === "ui") {
    return (
      <p className="text-sm text-gray-500 italic text-center">{message.text}</p>
    );
  }
  return (
    <>
      <strong>{message.type === "ai" ? "Bot: " : "You: "}</strong>
      <div>
        {message.text.length === 0 ? (
          <span className="animate-dot-pulse italic">Thinking...</span>
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
                      // type prefix avoids bare index, which React warns against
                      return (
                        <RenderedChunk
                          key={chunkObj.type + index}
                          chunkObj={chunkObj}
                        />
                      );
                    } catch {
                      console.warn(
                        "MessageContent: failed to parse chunk as JSON, falling back to markdown:",
                        chunk,
                      );
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
