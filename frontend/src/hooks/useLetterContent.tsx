import { useMemo } from "react";
import type { ChatMessage } from "../shared/types/messages";
import type { LetterChunk, ResponseChunk } from "../types/models";

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
          return [JSON.parse(line) as ResponseChunk];
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
