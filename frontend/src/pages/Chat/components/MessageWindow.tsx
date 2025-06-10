import { useEffect, useRef, useState } from "react";
import type { IMessage } from "../../../hooks/useMessages";
import InputField from "./InputField";
import MessageContent from "./MessageContent";
import useSession from "../../../hooks/useSession";
import ExportMessagesButton from "./ExportMessagesButton";


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
  const { handleNewSession } = useSession();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  const handleClearSession = () => {
    handleNewSession();
    setMessages([]);
  };

  useEffect(() => {
    inputRef.current?.focus();
    const messagesElement = messagesRef.current;
    if (messagesElement) {
      messagesElement.scrollTo({
        top: messagesElement.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

  return (
    <>
      <div>

        {isError ? (
          <div className="flex items-center justify-center h-full text-center">
            Error fetching chat history. Try refreshing...
          </div>
        ) : (
          <div
            className={`max-h-[calc(100vh-25rem)] mx-auto max-w-[700px] ${isOngoing ? "overflow-y-scroll" : "overflow-y-none"
              }`}
            ref={messagesRef}
          >
            {isOngoing ? (
              <div className="flex flex-col gap-4">
                {messages.map((message) => (
                  <div
                    className={`flex w-full ${message.role === "assistant"
                      ? "justify-start"
                      : "justify-end"
                      }`}
                    key={message.messageId}
                  >
                    <div
                      className={`p-3 rounded-2xl max-w-[95%] ${message.role === "assistant"
                        ? "bg-gray-100 rounded-tl-sm"
                        : "bg-[#4a90e2] text-white rounded-tr-sm"
                        }`}
                    >
                      <MessageContent message={message} isLoading={isLoading} onStatuteClick={onStatuteClick} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-[#888]">
                Ask me anything about tenant rights and assistance.
              </p>
            )}
          </div>
        )}
      </div>
      <div>
        <InputField
          setMessages={setMessages}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
          inputRef={inputRef}
        />
        {messages.length > 0 ? (
          <div className="flex justify-center gap-4 mt-4">
            <button
              className="flex items-center gap-2 px-4 py-2 rounded-md border border-gray-300 bg-white text-[#E3574B] font-semibold shadow-sm hover:bg-[#fff0ee] hover:border-[#E3574B] transition-colors"
              onClick={handleClearSession}
              title="Clear Chat"
            >

              Clear Chat
            </button>
            <div className="">
              <ExportMessagesButton
                messages={messages}

              />
            </div>
          </div>
        ) : null}

      </div>
    </>
  );
}
