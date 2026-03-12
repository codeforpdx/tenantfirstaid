import { AIMessage } from "@langchain/core/messages";
import type { Location } from "../../../types/models";
import type { ChatMessage, UiMessage } from "../../../shared/types/messages";

/**
 * Options for streaming AI responses into the chat message list.
 */
export interface StreamTextOptions {
  addMessage: (
    args: Location,
  ) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  housingLocation: Location;
  setIsLoading?: React.Dispatch<React.SetStateAction<boolean>>;
}

/**
 * Streams text from the AI model and updates messages in real-time.
 *
 * @returns Promise that resolves to:
 *   - `true` if streaming completed successfully
 *   - `undefined` if reader is not available or an error occurred
 */
async function streamText({
  addMessage,
  setMessages,
  housingLocation,
  setIsLoading,
}: StreamTextOptions): Promise<boolean | undefined> {
  const botMessageId = (Date.now() + 1).toString();

  setIsLoading?.(true);

  // Add empty bot message immediately so "Typing..." appears before the API responds.
  setMessages((prev) => [
    ...prev,
    new AIMessage({ content: "", id: botMessageId }),
  ]);

  try {
    const reader = await addMessage(housingLocation);
    if (!reader) {
      console.error("Stream reader is unavailable");
      const nullReaderError: UiMessage = {
        type: "ui",
        text: "Sorry, I encountered an error. Please try again.",
        id: botMessageId,
      };
      setMessages((prev) =>
        prev.map((msg) => (msg.id === botMessageId ? nullReaderError : msg)),
      );
      return;
    }
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    const processLines = (lines: string[]) => {
      lines
        .filter((line) => line.trim() !== "")
        .forEach((processedText) => {
          fullText += processedText + "\n";
          // Update only the bot's message
          const botMessage = new AIMessage({
            content: fullText,
            id: botMessageId,
          });
          setMessages((prev) =>
            prev.map((msg) => (msg.id === botMessageId ? botMessage : msg)),
          );
        });
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // Flush any remaining content in the buffer.
        if (buffer.trim() !== "") processLines([buffer]);
        return true;
      }
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      processLines(lines);
    }
  } catch (error) {
    console.error("Error:", error);
    const errorMessage: UiMessage = {
      type: "ui",
      text: "Sorry, I encountered an error. Please try again.",
      id: botMessageId,
    };
    setMessages((prev) => [
      ...prev.filter((msg) => msg.id !== botMessageId),
      errorMessage,
    ]);
  } finally {
    setIsLoading?.(false);
  }
}

export { streamText };
