import { useCallback, useEffect } from "react";
import { type IMessage } from "../../../hooks/useMessages";
import { ILocation } from "../../../hooks/useLocation";
import { streamText } from "../utils/streamHelper";

interface Props {
  addMessage: (args: {
    city: string | null;
    state: string;
  }) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  isLoading: boolean;
  location: ILocation;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  value: string;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

export default function InputField({
  addMessage,
  setMessages,
  isLoading,
  location,
  setIsLoading,
  inputRef,
  value,
  onChange,
}: Props) {
  const handleSend = async () => {
    if (!value.trim()) return;

    onChange({
      target: { value: "" },
    } as React.ChangeEvent<HTMLTextAreaElement>);

    const userMessageId = Date.now().toString();
    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: "user", content: value, messageId: userMessageId },
    ]);

    await streamText({
      addMessage,
      setMessages,
      location,
      setIsLoading,
    });
  };

  const resizeTextArea = useCallback(() => {
    const inputElement = inputRef.current;
    if (inputElement !== null) {
      inputElement.style.height = "auto";
      inputElement.style.height = `${inputElement.scrollHeight}px`;
    }
  }, [inputRef]);

  useEffect(() => {
    resizeTextArea();
  }, [value, resizeTextArea]);

  return (
    <div className="flex gap-2 mt-4 justify-center items-center mx-auto max-w-[700px]">
      <label htmlFor="chat-input" className="sr-only">
        Type your message
      </label>
      <textarea
        id="chat-input"
        value={value}
        onChange={onChange}
        onInput={resizeTextArea}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            handleSend();
          }
        }}
        rows={1}
        className="overflow-auto resize-none max-h-22 w-full px-3 py-2 border border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
        placeholder="Type your message here..."
        disabled={isLoading}
        ref={inputRef}
        aria-label="Chat message input"
        aria-describedby={isLoading ? "loading-status" : undefined}
      />
      <button
        className={`px-6 h-10 bg-[#1F584F] hover:bg-[#4F8B82] text-white rounded-md transition-color duration-300 ${isLoading ? "cursor-progress" : "cursor-pointer"}`}
        onClick={handleSend}
        disabled={isLoading || !value.trim()}
        aria-label={isLoading ? "Sending message..." : "Send message"}
      >
        {isLoading ? "..." : "Send"}
      </button>
      {isLoading && (
        <span id="loading-status" className="sr-only" aria-live="polite">
          Sending message and waiting for response...
        </span>
      )}
    </div>
  );
}
