import React, { useEffect, useRef, useState } from "react";
import { render, renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HumanMessage, AIMessage } from "@langchain/core/messages";
import useMessages, { deserializeAiMessage } from "../../hooks/useMessages";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    QueryClientProvider,
    { client: new QueryClient() },
    children,
  );
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

describe("useMessages", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts with empty messages when no storageKey is given", () => {
    const { result } = renderHook(() => useMessages(), { wrapper });
    expect(result.current.messages).toEqual([]);
  });

  it("starts with empty messages when storageKey has no entry", () => {
    const { result } = renderHook(() => useMessages("test_key"), { wrapper });
    expect(result.current.messages).toEqual([]);
  });

  it("loads messages from sessionStorage on init", () => {
    const stored = [
      { type: "human", content: "hello", id: "1" },
      { type: "ai", content: "world", id: "2" },
    ];
    sessionStorage.setItem("test_key", JSON.stringify(stored));

    const { result } = renderHook(() => useMessages("test_key"), { wrapper });
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toBeInstanceOf(HumanMessage);
    expect(result.current.messages[1]).toBeInstanceOf(AIMessage);
  });

  it("persists messages to sessionStorage when they change", () => {
    const { result } = renderHook(() => useMessages("test_key"), { wrapper });

    act(() => {
      result.current.setMessages([
        new HumanMessage({ content: "hi", id: "1" }),
      ]);
    });

    const stored = JSON.parse(sessionStorage.getItem("test_key") ?? "[]");
    expect(stored).toEqual([{ type: "human", content: "hi", id: "1" }]);
  });

  it("preserves and sends a guarded initial message in Strict Mode", async () => {
    const reader = {} as ReadableStreamDefaultReader<Uint8Array>;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      body: { getReader: () => reader },
    } as Response);

    function LetterBootstrap() {
      const { messages, setMessages, addMessage } =
        useMessages("letter_messages:or-portland,");
      const hasInitialized = useRef(false);
      const [startStreaming, setStartStreaming] = useState(false);

      useEffect(() => {
        if (hasInitialized.current) return;
        hasInitialized.current = true;
        setMessages((previous) => [
          ...previous,
          new HumanMessage({ content: "Generate my letter", id: "1" }),
        ]);
        setStartStreaming(true);
      }, [setMessages]);

      useEffect(() => {
        if (!startStreaming) return;
        setStartStreaming(false);
        void addMessage({ city: "portland", state: "or" });
      }, [addMessage, startStreaming]);

      return React.createElement(
        "div",
        { "data-testid": "message-count" },
        messages.length,
      );
    }

    const view = render(
      React.createElement(
        React.StrictMode,
        null,
        React.createElement(
          QueryClientProvider,
          { client: new QueryClient() },
          React.createElement(LetterBootstrap),
        ),
      ),
    );

    await waitFor(() => {
      expect(view.getByTestId("message-count").textContent).toBe("1");
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    expect(
      JSON.parse(
        sessionStorage.getItem("letter_messages:or-portland,") ?? "[]",
      ),
    ).toEqual([
        { type: "human", content: "Generate my letter", id: "1" },
    ]);

    const request = fetchSpy.mock.calls[0]?.[1];
    expect(JSON.parse(String(request?.body))).toEqual({
      messages: [
        { role: "human", content: "Generate my letter", id: "1" },
      ],
      city: "portland",
      state: "or",
    });
  });

  it("loads a new storage key without copying the previous conversation", async () => {
    sessionStorage.setItem(
      "second_key",
      JSON.stringify([{ type: "human", content: "second", id: "2" }]),
    );
    const { result, rerender } = renderHook(
      ({ storageKey }) => useMessages(storageKey),
      {
        initialProps: { storageKey: "first_key" },
        wrapper,
      },
    );

    act(() => {
      result.current.setMessages([
        new HumanMessage({ content: "first", id: "1" }),
      ]);
    });

    rerender({ storageKey: "second_key" });

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].text).toBe("second");
    });

    expect(JSON.parse(sessionStorage.getItem("first_key") ?? "[]")).toEqual([
      { type: "human", content: "first", id: "1" },
    ]);
    expect(JSON.parse(sessionStorage.getItem("second_key") ?? "[]")).toEqual([
      { type: "human", content: "second", id: "2" },
    ]);
  });

  it("clearMessages resets state and removes the sessionStorage entry", () => {
    sessionStorage.setItem(
      "test_key",
      JSON.stringify([{ type: "human", content: "hi", id: "1" }]),
    );
    const { result } = renderHook(() => useMessages("test_key"), { wrapper });

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
    expect(sessionStorage.getItem("test_key")).toBeNull();
  });

  it("clearMessages without a storageKey only resets state", () => {
    const { result } = renderHook(() => useMessages(), { wrapper });

    act(() => {
      result.current.setMessages([
        new HumanMessage({ content: "hi", id: "1" }),
      ]);
    });

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
  });
});
