import { useMemo } from "react";
import type { ChatMessage } from "../shared/types/messages";
import type { LetterChunk, ResponseChunk } from "../types/models";

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

  return (
    type === "text" ||
    type === "reasoning" ||
    type === "letter" ||
    type === "end_of_stream"
  );
}

/**
 * Extracts generated letter content from chat messages by scanning all AI
 * messages and returning the last letter chunk found.
 */
export function useLetterContent(messages: ChatMessage[]) {
  const letterContent = useMemo(() => {
    const chunks = messages
      .filter((msg) => msg.type === "ai")
      .flatMap((msg) => msg.text.split("\n").filter(Boolean))
      .flatMap((line) => {
        try {
          const parsed = JSON.parse(line);
          if (isResponseChunk(parsed)) {
            return [parsed];
          }
          return []; // Not a valid ResponseChunk — skip.
        } catch {
          return []; // Not a JSON chunk — skip.
        }
      });

    const letterChunks = chunks.filter(
      (chunk): chunk is LetterChunk => chunk.type === "letter",
    );
    return letterChunks[letterChunks.length - 1]?.content ?? "";
  }, [messages]);

  return { letterContent };
}
