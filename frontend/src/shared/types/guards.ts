import type { ResponseChunk } from "../../types/models";

type ChunkType = NonNullable<ResponseChunk["type"]>;

// Keys must exactly match ChunkType. If schema.py grows a new chunk variant,
// models.ts regenerates with a wider union and this object literal fails to
// typecheck instead of silently rejecting the new chunk.
const responseChunkTypes: Record<ChunkType, true> = {
  text: true,
  reasoning: true,
  letter: true,
  end_of_stream: true,
};

// Compile-time-only assertion, decoupled from the Record annotation above:
// fails to typecheck if `responseChunkTypes`' keys and ChunkType ever
// diverge in either direction, even if the annotation on the object above
// is loosened or removed later.
type AssertEqual<A, B> = A extends B ? (B extends A ? true : never) : never;
export type AssertChunkTypesExhaustive = AssertEqual<
  keyof typeof responseChunkTypes,
  ChunkType
>;

/**
 * Type guard to validate that a parsed object is a ResponseChunk.
 * A valid ResponseChunk must have a 'type' property that is one of the allowed types.
 */
export function isResponseChunk(obj: unknown): obj is ResponseChunk {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }

  const type = (obj as { type?: unknown }).type;
  return typeof type === "string" && type in responseChunkTypes;
}
