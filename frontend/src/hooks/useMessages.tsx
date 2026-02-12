import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { MessageType } from "@langchain/core/messages";

/**
 * Chat message interface aligned with LangChain's message types.
 * Uses LangChain MessageType for role to ensure consistency with backend.
 */
export interface IChatMessage {
  role: Extract<MessageType, "human" | "ai">;
  content: string;
  id: string;
}

async function addNewMessage(
  messages: IChatMessage[],
  city: string | null,
  state: string,
) {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ messages: messages, city, state }),
  });
  return response.body?.getReader();
}

/**
 * Hook for managing chat messages and sending queries to the backend.
 * Provides message state, a setter, and a mutation for posting new messages.
 */
export default function useMessages() {
  const [messages, setMessages] = useState<IChatMessage[]>([]);

  const addMessage = useMutation({
    mutationFn: async ({
      city,
      state,
    }: {
      city: string | null;
      state: string;
    }) => {
      const filteredMessages = messages.filter(
        (msg) => msg.content.trim() !== "",
      ); // Filters out empty bot message
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
