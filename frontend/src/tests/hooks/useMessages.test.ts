import { createElement, type ReactNode } from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import useMessages, { deserializeAiMessage } from "../../hooks/useMessages";

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

function wrapper({ children }: { children: ReactNode }) {
  return createElement(
    QueryClientProvider,
    { client: new QueryClient() },
    children,
  );
}

describe("useMessages addMessage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the given messages, excluding UI messages and empty placeholders", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("ok"));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useMessages(), { wrapper });

    await result.current.addMessage({
      messages: [
        new HumanMessage({ content: "My heat is broken", id: "1" }),
        new AIMessage({ content: "", id: "2" }),
        { type: "ui", text: "Info", id: "3" },
      ],
      city: "portland",
      state: "or",
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toEqual({
      messages: [{ role: "human", content: "My heat is broken", id: "1" }],
      city: "portland",
      state: "or",
    });
  });

  it("rejects instead of streaming the body when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("<html>502 Bad Gateway</html>", { status: 502 }),
        ),
    );
    const { result } = renderHook(() => useMessages(), { wrapper });

    await expect(
      result.current.addMessage({ messages: [], city: null, state: "or" }),
    ).rejects.toThrow("502");
  });
});
