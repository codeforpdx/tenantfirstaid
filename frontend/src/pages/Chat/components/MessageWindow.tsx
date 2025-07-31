import { useEffect, useRef, useState } from "react";
import type { IMessage } from "../../../hooks/useMessages";
import InputField from "./InputField";
import MessageContent from "./MessageContent";
import useSession from "../../../hooks/useSession";
import ExportMessagesButton from "./ExportMessagesButton";
import CitySelectField from "./CitySelectField";
import SuggestedPrompts from "./SuggestedPrompts";

interface Props {
  messages: IMessage[];
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  isOngoing: boolean;
  isError: boolean;
  onStatuteClick: (statute: string) => void;
}

export default function MessageWindow({
  messages,
  setMessages,
  isOngoing,
  isError,
  onStatuteClick,
}: Props) {
  const [isLoading, setIsLoading] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const { handleNewSession } = useSession();
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  const handleClearSession = () => {
    handleNewSession();
    window.location.reload();
  };

  useEffect(() => {
    const messagesElement = messagesRef.current;
    if (messagesElement) {
      messagesElement.scrollTo({
        top: messagesElement.scrollHeight,
        behavior: "smooth",
      });
      setTimeout(() => {
        inputRef.current?.focus();
      }, 500);
    }
  }, [messages]);

  const handlePromptClick = (prompt: string) => {
    setInputValue(prompt);
    if (inputRef.current) {
      inputRef.current.value = prompt;
      inputRef.current.focus();
    }
  };

  return (
    <>
      <div
        className={`flex-1 ${isOngoing ? "overflow-y-scroll" : "overflow-y-none"
          }`}
        ref={messagesRef}
      >
        {isError ? (
          <div className="flex items-center justify-center h-full text-center">
            Error fetching chat history. Try refreshing...
          </div>
        ) : (
          <div className="max-h-[calc(100dvh-240px)] sm:max-h-[calc(100dvh-20rem)] mx-auto max-w-[700px]">
            {isOngoing ? (
              <div className="flex flex-col gap-4">
                {messages.map((message) => (
                  <div
                    className={`flex w-full ${message.role === "model"
                        ? "justify-start"
                        : "justify-end"
                      }`}
                    key={message.messageId}
                  >
                    <div
                      className={`message-bubble p-3 rounded-2xl max-w-[95%] ${message.role === "model"
                          ? "bg-slate-200 rounded-tl-sm"
                          : "bg-[#1F584F] text-white rounded-tr-sm"
                        }`}
                    >
                      <MessageContent
                        message={message}
                        isLoading={isLoading}
                        onStatuteClick={onStatuteClick}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        )}
      </div>
      <div>
        {messages.length > 0 ? (
          <>
            {messages.length === 1 && inputValue === "" && (
              <SuggestedPrompts onPromptClick={handlePromptClick} />
            )}
            <InputField
              setMessages={setMessages}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              inputRef={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <div className="flex justify-center gap-4 mt-4">
              <button
                className="flex items-center gap-2 px-4 py-2 rounded-md border border-gray-300 text-[#E3574B] font-semibold shadow-sm hover:bg-[#fff0ee] hover:border-[#E3574B] transition-colors cursor-pointer"
                onClick={handleClearSession}
                title="Clear Chat"
              >
                Clear Chat
              </button>
              <div className="">
                <ExportMessagesButton messages={messages} />
              </div>
            </div>
          </>
        ) : (
          <CitySelectField setMessages={setMessages} />
        )}
      </div>
    </>
  );
}
