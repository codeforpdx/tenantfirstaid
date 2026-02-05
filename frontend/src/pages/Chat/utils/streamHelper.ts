import { ILocation } from "../../../contexts/HousingContext";
import { type IMessage } from "../../../hooks/useMessages";

interface IStreamTextOptions {
  addMessage: (args: {
    city: string | null;
    state: string;
  }) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  housingLocation: ILocation;
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
}: IStreamTextOptions): Promise<boolean | undefined> {
  const botMessageId = (Date.now() + 1).toString();

  setIsLoading?.(true);

  // Add empty bot message that will be updated
  setMessages((prev) => [
    ...prev,
    {
      role: "ai",
      content: "",
      messageId: botMessageId,
    },
  ]);

  try {
    const reader = await addMessage({
      city: housingLocation?.city,
      state: housingLocation?.state || "",
    });
    if (!reader) {
      console.error("Stream reader is unavailable");
      return;
    }
    const decoder = new TextDecoder();
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) return true;
      const chunk = decoder.decode(value);
      fullText += chunk;

      // Update only the bot's message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.messageId === botMessageId ? { ...msg, content: fullText } : msg,
        ),
      );
    }
  } catch (error) {
    console.error("Error:", error);
    setMessages((prev) =>
      prev.map((msg) =>
        msg.messageId === botMessageId
          ? {
              ...msg,
              content: "Sorry, I encountered an error. Please try again.",
            }
          : msg,
      ),
    );
  } finally {
    setIsLoading?.(false);
  }
}

export { streamText };
