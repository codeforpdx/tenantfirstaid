import { renderHook } from "@testing-library/react";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { describe, it, expect } from "vitest";
import { useLetterContent } from "../../hooks/useLetterContent";
import type { TChatMessage } from "../../hooks/useMessages";

const letterChunk =
  '{"type":"letter","content":"Dear Landlord, please fix the heat."}\n';
const textChunk = '{"type":"text","content":"Here is your letter."}\n';

describe("useLetterContent", () => {
  it("returns letter content from a letter chunk in an AI message", () => {
    const messages: TChatMessage[] = [
      new AIMessage({ content: textChunk + letterChunk, id: "1" }),
    ];
    const { result } = renderHook(() => useLetterContent(messages));
    expect(result.current.letterContent).toBe(
      "Dear Landlord, please fix the heat.",
    );
  });

  it("returns the last letter chunk when multiple messages contain one", () => {
    const messages: TChatMessage[] = [
      new AIMessage({
        content: '{"type":"letter","content":"Old letter."}\n',
        id: "1",
      }),
      new AIMessage({
        content: '{"type":"letter","content":"New letter."}\n',
        id: "2",
      }),
    ];
    const { result } = renderHook(() => useLetterContent(messages));
    expect(result.current.letterContent).toBe("New letter.");
  });

  it("returns empty string when no message contains a letter chunk", () => {
    const messages: TChatMessage[] = [
      new HumanMessage({ content: "Write me a letter.", id: "1" }),
      new AIMessage({ content: textChunk, id: "2" }),
    ];
    const { result } = renderHook(() => useLetterContent(messages));
    expect(result.current.letterContent).toBe("");
  });
});
