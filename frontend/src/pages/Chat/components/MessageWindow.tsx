import { useEffect, useRef, useState } from "react";
import type { IMessage } from "../../../hooks/useMessages";
import InputField from "./InputField";
import MessageContent from "./MessageContent";
import ExportMessagesButton from "./ExportMessagesButton";
import CitySelectField from "./CitySelectField";
import SuggestedPrompts from "./SuggestedPrompts";
import { ILocation } from "../../../hooks/useLocation";

interface Props {
  messages: IMessage[];
  addMessage: (args: {
    city: string | null;
    state: string;
  }) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
  location: ILocation;
  setLocation: React.Dispatch<React.SetStateAction<ILocation>>;
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  isOngoing: boolean;
}

export default function MessageWindow({
  messages,
  addMessage,
  location,
  setMessages,
  setLocation,
  isOngoing,
}: Props) {
  const [isLoading, setIsLoading] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  const handleClearSession = () => {
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
        className={`flex-1 ${
          isOngoing ? "overflow-y-scroll" : "overflow-y-none"
        }`}
        ref={messagesRef}
      >
        <div className="max-h-[calc(100dvh-240px)] sm:max-h-[calc(100dvh-20rem)] mx-auto max-w-[700px]">
          {isOngoing ? (
            <div className="flex flex-col gap-4">
              {messages.map((message) => (
                <div
                  className={`flex w-full ${
                    message.role === "model" ? "justify-start" : "justify-end"
                  }`}
                  key={message.messageId}
                >
                  <div
                    className={`message-bubble p-3 rounded-2xl max-w-[95%] ${
                      message.role === "model"
                        ? "bg-slate-200 rounded-tl-sm"
                        : "bg-[#1F584F] text-white rounded-tr-sm"
                    }`}
                  >
                    <MessageContent message={message} isLoading={isLoading} />
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      <div>
        {messages.length > 0 ? (
          <>
            {messages.length === 1 && inputValue === "" && (
              <SuggestedPrompts onPromptClick={handlePromptClick} />
            )}
            <InputField
              addMessage={addMessage}
              setMessages={setMessages}
              isLoading={isLoading}
              location={location}
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
          <CitySelectField
            setMessages={setMessages}
            setLocation={setLocation}
          />
        )}
      </div>
    </>
  );
}
