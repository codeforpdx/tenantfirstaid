import { renderHook, waitFor } from "@testing-library/react";
import { useState } from "react";
import { AIMessage } from "@langchain/core/messages";
import { describe, it, expect } from "vitest";
import { useLetterContent } from "../../hooks/useLetterContent";
import type { TChatMessage } from "../../hooks/useMessages";

const letterOnlyMessage = new AIMessage({
  content: "-----generate letter-----<p>Letter HTML</p>-----end of letter-----",
  id: "1",
});

describe("useLetterContent", () => {
  it("uses fallback text when the response contains only the letter block", async () => {
    const { result } = renderHook(() => {
      const [messages, setMessages] = useState<TChatMessage[]>([letterOnlyMessage]);
      const { letterContent } = useLetterContent(messages, setMessages);
      return { messages, letterContent };
    });

    await waitFor(() => {
      expect(result.current.messages[0].text).toBe(
        "Here's the generated letter. Do you wish to modify it?",
      );
    });
  });
});
