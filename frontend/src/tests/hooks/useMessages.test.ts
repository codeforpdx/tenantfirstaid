import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { createElement } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HumanMessage, AIMessage } from "@langchain/core/messages";
import type { ChatMessage, UiMessage } from "../../shared/types/messages";
import useMessages, { deserializeAiMessage } from "../../hooks/useMessages";

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

async function callAddMessage(messagesToSet: ChatMessage[]) {
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
    body: { getReader: vi.fn() },
  } as unknown as Response);

  const { result } = renderHook(() => useMessages(), {
    wrapper: makeWrapper(),
  });

  act(() => {
    result.current.setMessages(messagesToSet);
  });

  await act(async () => {
    await result.current.addMessage({ city: "portland", state: "or" });
  });

  return JSON.parse((fetchSpy.mock.calls[0][1] as RequestInit).body as string);
}

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

describe("useMessages hook", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("initializes with empty messages and exposes setMessages and addMessage", () => {
    const { result } = renderHook(() => useMessages(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.messages).toEqual([]);
    expect(typeof result.current.setMessages).toBe("function");
    expect(typeof result.current.addMessage).toBe("function");
  });

  it("POSTs serialized messages to /api/query", async () => {
    const mockReader = {};
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      body: { getReader: () => mockReader },
    } as unknown as Response);

    const { result } = renderHook(() => useMessages(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.setMessages([
        new HumanMessage({ content: "hello", id: "1" }),
      ]);
    });

    await act(async () => {
      await result.current.addMessage({ city: "portland", state: "or" });
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/query",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "human", content: "hello", id: "1" }],
          city: "portland",
          state: "or",
        }),
      }),
    );
  });

  it("filters out UI messages before sending", async () => {
    const uiMsg: UiMessage = { type: "ui", text: "Typing...", id: "ui-1" };
    const body = await callAddMessage([
      new HumanMessage({ content: "hello", id: "1" }),
      uiMsg,
    ]);
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0].role).toBe("human");
  });

  it("filters out empty messages before sending", async () => {
    const body = await callAddMessage([
      new HumanMessage({ content: "hello", id: "1" }),
      new AIMessage({ content: "", id: "2" }),
    ]);
    expect(body.messages).toHaveLength(1);
    expect(body.messages[0].role).toBe("human");
  });

  it("deserializes AI message content before sending", async () => {
    const body = await callAddMessage([
      new AIMessage({
        content: '{"type":"text","content":"Hello"}\n',
        id: "2",
      }),
    ]);
    expect(body.messages[0].content).toBe("Hello");
  });
});
