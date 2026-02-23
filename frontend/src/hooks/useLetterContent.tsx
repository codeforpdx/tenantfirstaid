import { useMemo } from "react";
import { TChatMessage } from "./useMessages";
import type { TResponseChunk } from "../types/MessageTypes";

/**
 * Extracts generated letter content from chat messages by scanning for
 * letter chunks in the most recent AI message that contains one.
 */
export function useLetterContent(messages: TChatMessage[]) {
  const letterContent = useMemo(() => {
    const chunks = messages
      .filter((msg) => msg.type === "ai")
      .flatMap((msg) => msg.text.split("\n").filter(Boolean))
      .flatMap((line) => {
        try {
          return [JSON.parse(line) as TResponseChunk];
        } catch {
          return []; // Not a JSON chunk — skip.
        }
      });

    const letterChunks = chunks.filter((chunk) => chunk.type === "letter");
    return letterChunks[letterChunks.length - 1]?.letter ?? "";
  }, [messages]);

  return { letterContent };
}
