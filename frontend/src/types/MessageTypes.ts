interface ITextChunk {
  type: "text";
  content: string;
}

interface IReasoningChunk {
  type: "reasoning";
  content: string;
}

interface ILetterChunk {
  type: "letter";
  content: string;
}

type TResponseChunk = ITextChunk | IReasoningChunk | ILetterChunk;

export type { TResponseChunk, IReasoningChunk, ITextChunk, ILetterChunk };
