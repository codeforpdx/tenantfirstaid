interface ITextChunk {
  type: "text";
  text: string;
}

interface IReasoningChunk {
  type: "reasoning";
  reasoning: string;
}

interface ILetterChunk {
  type: "letter";
  letter: string;
}

type TResponseChunk = ITextChunk | IReasoningChunk | ILetterChunk;

export type { TResponseChunk, IReasoningChunk, ITextChunk, ILetterChunk };
