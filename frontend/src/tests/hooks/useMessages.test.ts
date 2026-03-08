import { describe, it, expect } from "vitest";
import { deserializeAiMessage } from "../../hooks/useMessages";

describe("deserializeAiMessage", () => {
  it("extracts text from a text chunk", () => {
    const input = '{"type":"text","content":"Here is the answer."}\n';
    expect(deserializeAiMessage(input)).toBe("Here is the answer.");
  });

  it("drops reasoning chunks", () => {
    const input =
      '{"type":"reasoning","content":"Let me think."}\n{"type":"text","content":"Here is the answer."}\n';
    expect(deserializeAiMessage(input)).toBe("Here is the answer.");
  });

  it("handles mixed text and letter chunks", () => {
    const input =
      '{"type":"text","content":"Here\'s a draft letter."}\n{"type":"letter","content":"Dear Landlord,"}\n';
    expect(deserializeAiMessage(input)).toBe(
      "Here's a draft letter.\nDear Landlord,",
    );
  });

  it("passes through plain-text lines unchanged", () => {
    const input = "What was generated is just an initial template.\n";
    expect(deserializeAiMessage(input)).toBe(
      "What was generated is just an initial template.",
    );
  });
});
