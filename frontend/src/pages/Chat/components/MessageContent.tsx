import SafeMarkdown from "../../../shared/components/SafeMarkdown";
import type { ChatMessage } from "../../../shared/types/messages";
import type { ResponseChunk } from "../../../types/models";

/**
 * Type guard to validate that a parsed object is a ResponseChunk.
 * A valid ResponseChunk must have a 'type' property that is one of the allowed types.
 */
function isResponseChunk(obj: unknown): obj is ResponseChunk {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }
  
  const type = (obj as { type?: unknown }).type;
  if (typeof type !== "string") {
    return false;
  }
  
  return type === "text" || type === "reasoning" || type === "letter" || type === "end_of_stream";
}

/**
 * Safely parses a string as a ResponseChunk.
 * Returns the parsed chunk if valid, null otherwise.
 */
function parseResponseChunk(text: string): ResponseChunk | null {
  try {
    const parsed = JSON.parse(text);
    return isResponseChunk(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

interface ChunkProps {
  chunkObj: ResponseChunk;
}

function RenderedChunk({ chunkObj }: ChunkProps) {
  switch (chunkObj.type) {
    case "text":
      return <SafeMarkdown>{chunkObj.content}</SafeMarkdown>;
    case "reasoning":
      return (
        <div className="flex gap-2 my-2">
          {/* reasoning chunk is styled to help differentiate reasoning from text */}
          {`\u{1F914}`}
          <em className="text-slate-500 leading-relaxed">{chunkObj.content}</em>
        </div>
      );
    // No letter case (chunk handled in letter panel)
    default:
      return null;
  }
}

/** Returns true if an AI message has content that will visibly render. */
function hasRenderableContent(text: string): boolean {
  return text
    .split("\n")
    .filter(Boolean)
    .some((chunk) => {
      const parsed = parseResponseChunk(chunk);
      if (!parsed) {
        return true;
      }
      return (
        (parsed.type === "text" && (parsed.content?.length ?? 0) > 0) ||
        (parsed.type === "reasoning" && (parsed.content?.length ?? 0) > 0)
      );
    });
}

interface Props {
  message: ChatMessage;
}

/**
 * Renders a single chat message bubble.
 * AI messages are parsed as newline-delimited JSON chunks and rendered as markdown.
 * Human messages are rendered as plain markdown.
 */
export default function MessageContent({ message }: Props) {
  if (message.type === "ui") {
    return (
      <>
        <strong>Info: </strong>
        <p className="italic">{message.text}</p>
      </>
    );
  }

  const isThinking =
    message.type === "ai"
      ? !hasRenderableContent(message.text)
      : message.text.length === 0;

  return (
    <>
      <strong>{message.type === "ai" ? "Brainy: " : "You: "}</strong>
      <div>
        {isThinking ? (
          <span className="animate-dot-pulse italic">Thinking...</span>
        ) : (
          <>
            {message.type === "ai" ? (
              <>
                {message.text
                  .split("\n")
                  .filter((chunk) => chunk.length !== 0)
                  .map((chunk, index) => {
                    const chunkObj = parseResponseChunk(chunk);
                    if (chunkObj) {
                      // type prefix avoids bare index, which React warns against
                      return (
                        <RenderedChunk
                          key={(chunkObj.type ?? "") + index}
                          chunkObj={chunkObj}
                        />
                      );
                    }
                    
                    console.warn(
                      "MessageContent: failed to parse chunk as ResponseChunk, falling back to markdown:",
                      chunk,
                    );
                    return (
                      <SafeMarkdown key={`automated-${index}`}>
                        {chunk}
                      </SafeMarkdown>
                    );
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
