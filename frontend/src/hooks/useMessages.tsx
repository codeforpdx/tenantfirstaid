import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export interface IMessage {
  role: "user" | "model";
  content: string;
  messageId: string;
}

async function addNewMessage(
  messages: IMessage[],
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

export default function useMessages() {
  const [messages, setMessages] = useState<IMessage[]>([]);

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
