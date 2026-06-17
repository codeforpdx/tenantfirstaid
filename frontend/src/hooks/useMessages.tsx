import { useMutation } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import type { Location } from "../types/models";
import type { ChatMessage, UiMessage } from "../shared/types/messages";
import { AIMessage, HumanMessage } from "@langchain/core/messages";


type StoredMessage = { type: "human" | "ai"; content: string; id: string };

function loadFromStorage(key: string): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return [];
    const stored: StoredMessage[] = JSON.parse(raw);
    return stored.map((msg) => 
      msg.type === "human" ? new HumanMessage({ content: msg.content, id: msg.id }) 
      : new AIMessage({ content: msg.content, id: msg.id })
    )
  } catch {
    return [];
  }
}
/**
 * Converts a stored AI message (JSONL chunks) back to plain text for backend
 * history.
 */
export function deserializeAiMessage(text: string): string {
  return text
    .split("\n")
    .filter(Boolean)
    .flatMap((line) => {
      try {
        const chunk = JSON.parse(line);
        if (["text", "letter"].includes(chunk.type)) return [chunk.content];
        return [];
      } catch {
        return [line]; // plain text
      }
    })
    .join("\n");
}

async function addNewMessage(
  messages: ChatMessage[],
  { city, state }: Location,
) {
  const serializedMsg = messages.map((msg) => ({
    role: msg.type,
    content: msg.type === "ai" ? deserializeAiMessage(msg.text) : msg.text,
    id: msg.id,
  }));
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ messages: serializedMsg, city, state }),
  });
  return response.body?.getReader();
}

/**
 * Hook for managing chat messages and sending queries to the backend.
 * Provides message state, a setter, and a mutation for posting new messages.
 */
export default function useMessages(storageKey?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    storageKey ? loadFromStorage(storageKey) : []
  );

  useEffect(() => {
    setMessages(storageKey ? loadFromStorage(storageKey) : []);
  }, [storageKey]);

  useEffect(() => {
    if (!storageKey) return;
    const toStore: StoredMessage[] = messages
    .filter(
      (msg): msg is Exclude<ChatMessage, UiMessage> => 
        msg.type !== "ui" && msg.text.trim() !== ""
    )
    .map((msg) => ({
      type: msg instanceof HumanMessage ? "human" : "ai",
      content: typeof msg.content === "string" ? msg.content : msg.text,
      id: msg.id ?? "",
    }));
    toStore.length === 0 ? sessionStorage.removeItem(storageKey) : sessionStorage.setItem(storageKey, JSON.stringify(toStore));
  }, [messages, storageKey])

  const addMessage = useMutation({
    mutationFn: async ({ city, state }: Location) => {
      // Exclude UI-only messages and empty placeholders from backend history.
      const filteredMessages = messages.filter(
        (msg): msg is Exclude<ChatMessage, UiMessage> =>
          msg.type !== "ui" && msg.text.trim() !== "",
      );
      return await addNewMessage(filteredMessages, { city, state });
    },
  });

  function clearMessages() {
    setMessages([]);
  }

  return {
    messages,
    setMessages,
    addMessage: addMessage.mutateAsync,
    clearMessages,
  };
}
