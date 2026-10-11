import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { Location } from "../types/models";
import type { ChatMessage, UiMessage } from "../shared/types/messages";

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

/** Arguments for sending the conversation history to the backend. */
export interface AddMessageArgs extends Location {
  messages: ChatMessage[];
}

export type AddMessage = (
  args: AddMessageArgs,
) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;

async function addNewMessage({ messages, city, state }: AddMessageArgs) {
  // Exclude UI-only messages and empty placeholders from backend history.
  const serializedMsg = messages
    .filter(
      (msg): msg is Exclude<ChatMessage, UiMessage> =>
        msg.type !== "ui" && msg.text.trim() !== "",
    )
    .map((msg) => ({
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
  if (!response.ok) {
    throw new Error(`Query failed with status ${response.status}`);
  }
  return response.body?.getReader();
}

/**
 * Hook for managing chat messages and sending queries to the backend.
 * Provides message state, a setter, and a mutation for posting new messages.
 */
export default function useMessages() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const addMessage = useMutation({ mutationFn: addNewMessage });

  return {
    messages,
    setMessages,
    addMessage: addMessage.mutateAsync,
  };
}
