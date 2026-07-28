import type { ResponseChunk } from "../../types/models";

/**
 * Type guard to validate that a parsed object is a ResponseChunk.
 * A valid ResponseChunk must have a 'type' property that is one of the allowed types.
 */
export function isResponseChunk(obj: unknown): obj is ResponseChunk {
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
