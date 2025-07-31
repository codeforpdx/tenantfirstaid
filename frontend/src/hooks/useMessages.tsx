import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export interface IMessage {
  role: "user" | "model";
  content: string;
  messageId: string;
}

async function fetchChatHistory() {
  try {
    const response = await fetch("/api/history", {
      credentials: "include",
    });
    let history: IMessage[] = await response.json();
    let messageId = Date.now();
    history = history.map((message: IMessage) => {
      messageId++;
      message.messageId = messageId.toString();
      return message;
    });
    return history;
  } catch (err) {
    console.error("Error fetching chat history:", err);
    throw new Error(`Failed to fetch chat history. ${err}`);
  }
}

async function addNewMessage(userMessage: string) {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ message: userMessage }),
  });
  return response.body?.getReader();
}

async function initNewChat(city: string | null, state: string) {
  const response = await fetch("/api/init", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ city, state }),
  });
  return response.body?.getReader();
}

export default function useMessages() {
  const [messages, setMessages] = useState<IMessage[]>([]);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["messages"],
    queryFn: async () => await fetchChatHistory(),
  });

  const addMessage = useMutation({
    mutationFn: async (userMessage: string) => await addNewMessage(userMessage),
  });

  const initChat = useMutation({
    mutationFn: async ({
      city,
      state,
    }: {
      city: string | null;
      state: string;
    }) => await initNewChat(city, state),
  });

  useEffect(() => {
    if (data && data.length !== 0) {
      setMessages(data);
    } else if (data && data.length === 0) {
      setMessages([]);
    }
  }, [data]);

  return {
    messages,
    setMessages,
    addMessage: addMessage.mutateAsync,
    initChat: initChat.mutateAsync,
    isLoading,
    isError,
  };
}
