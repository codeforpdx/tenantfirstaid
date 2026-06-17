import React from "react";
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
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
    expect(sessionStorage.getItem("test_key")).toBe("[]");
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
