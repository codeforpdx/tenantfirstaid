import { useCallback, useEffect } from "react";
import { HumanMessage } from "@langchain/core/messages";
import type { ChatMessage } from "../../../shared/types/messages";
import type { AddMessage } from "../../../hooks/useMessages";
import { streamText } from "../utils/streamHelper";
import { createId } from "../../../shared/utils/createId";
import useHousingContext from "../../../hooks/useHousingContext";
import clsx from "clsx";

interface Props {
  messages: ChatMessage[];
  addMessage: AddMessage;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  isLoading: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  value: string;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  setValue: (value: string) => void;
}

/**
 * Auto-resizing text input for composing and sending chat messages.
 */
export default function InputField({
  messages,
  addMessage,
  setMessages,
  isLoading,
  setIsLoading,
  inputRef,
  value,
  setValue,
}: Props) {
  const { housingLocation } = useHousingContext();

  const handleSend = async () => {
    if (!value.trim()) return;

    setValue("");

    const userMessage = new HumanMessage({
      content: value,
      id: createId(),
    });
    setMessages((prev) => [...prev, userMessage]);

    await streamText({
      addMessage,
      history: [...messages, userMessage],
      setMessages,
      housingLocation,
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
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onInput={resizeTextArea}
        onKeyDown={(e) => {
          // keyCode 229 covers Safari, which ends composition before keydown.
          if (
            e.key === "Enter" &&
            !e.shiftKey &&
            !e.nativeEvent.isComposing &&
            e.keyCode !== 229
          ) {
            e.preventDefault();
            handleSend();
          }
        }}
        rows={1}
        className="overflow-auto box-border max-h-40 w-full px-3 py-2"
        placeholder="Type your message here..."
        disabled={isLoading}
        ref={inputRef}
      />
      <button
        className={clsx(
          "h-10 text-sm sm:text-base text-white bg-green-dark hover:bg-green-medium",
          isLoading ? "cursor-progress" : "cursor-pointer",
        )}
        onClick={handleSend}
        disabled={isLoading || !value.trim()}
      >
        {isLoading ? "..." : "Send"}
      </button>
    </div>
  );
}
