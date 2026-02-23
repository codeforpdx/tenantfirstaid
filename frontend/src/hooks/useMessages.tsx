import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { AIMessage, HumanMessage } from "@langchain/core/messages";

/**
 * Chat message Type aligned with LangChain's message types
 * to ensure consistency with backend.
 */
export type TChatMessage = HumanMessage | AIMessage;

/**
 * Reconstructs the plain-text format from a stored AI message, which may
 * contain newline-delimited JSON chunks so it wouldn't echo JSON back
 */
export function deserializeAiMessage(text: string): string {
  return text
    .split("\n")
    .filter(Boolean)
    .flatMap((line) => {
      try {
        const chunk = JSON.parse(line);
        if (chunk.type === "text") return [chunk.text];
        if (chunk.type === "letter") return [chunk.letter];
        return [];
      } catch {
        return [line]; // plain text
      }
    })
    .join("\n");
}

async function addNewMessage(
  messages: TChatMessage[],
  city: string | null,
  state: string,
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
export default function useMessages() {
  const [messages, setMessages] = useState<TChatMessage[]>([]);

  const addMessage = useMutation({
    mutationFn: async ({
      city,
      state,
    }: {
      city: string | null;
      state: string;
    }) => {
      const filteredMessages = messages.filter((msg) => msg.text.trim() !== ""); // Filters out empty bot message
      return await addNewMessage(filteredMessages, city, state);
    },
  });

  return {
    messages,
    setMessages,
    addMessage: addMessage.mutateAsync,
  };
}
