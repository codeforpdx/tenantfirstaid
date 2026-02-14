import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { AIMessage, HumanMessage } from "@langchain/core/messages";

/**
 * Chat message Type aligned with LangChain's message types
 * to ensure consistency with backend.
 */
export type TChatMessage = HumanMessage | AIMessage;

async function addNewMessage(
  messages: TChatMessage[],
  city: string | null,
  state: string,
) {
  const serializedMsg = messages.map((msg) => ({
    role: msg.type,
    content: msg.text,
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

  useEffect(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    setMessages,
    addMessage: addMessage.mutateAsync,
  };
}
