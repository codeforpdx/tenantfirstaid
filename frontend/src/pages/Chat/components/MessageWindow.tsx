import { useEffect, useRef, useState } from "react";
import type { IMessage } from "../../../hooks/useMessages";
import InputField from "./InputField";
import MessageContent from "./MessageContent";
import ExportMessagesButton from "./ExportMessagesButton";
import InitializationForm from "./InitializationForm";
import FeedbackModal from "./FeedbackModal";
import { useLocation } from "react-router-dom";

interface Props {
  messages: IMessage[];
  addMessage: (args: {
    city: string | null;
    state: string;
  }) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  isOngoing: boolean;
}

export default function MessageWindow({
  messages,
  addMessage,
  setMessages,
  isOngoing,
}: Props) {
  const [isLoading, setIsLoading] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [openFeedback, setOpenFeedback] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const loc = useLocation();

  // To hide initial prompt and response for letter generation
  const LETTER_PAGE_HIDDEN_MESSAGES = 2;
  const displayedMessages = loc.pathname.startsWith("/letter")
    ? messages.slice(LETTER_PAGE_HIDDEN_MESSAGES)
    : messages;

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

  return (
    <>
      <div
        className={`flex-1 ${
          isOngoing ? "overflow-y-scroll" : "overflow-y-none"
        }`}
        ref={messagesRef}
      >
        <div className="max-h-[calc(100dvh-var(--message-window-offset)-var(--navbar-height))] mx-auto max-w-[700px]">
          {isOngoing ? (
            <div className="flex flex-col gap-4 relative">
              {displayedMessages.map((message) => {
                return (
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
                          : "bg-green-dark text-white rounded-tr-sm"
                      }`}
                    >
                      <MessageContent message={message} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      </div>
      {openFeedback && (
        <FeedbackModal messages={messages} setOpenFeedback={setOpenFeedback} />
      )}
      <div>
        {messages.length > 0 ? (
          <>
            <InputField
              addMessage={addMessage}
              setMessages={setMessages}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              inputRef={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <div className="flex justify-center gap-4 mt-4">
              <button
                className={`
                  text-sm sm:text-base text-red-dark
                  border border-red-medium hover:border-red-dark
                  hover:bg-red-light`}
                onClick={handleClearSession}
                aria-label="clear chat"
                title="Clear Chat"
              >
                Clear
              </button>
              <ExportMessagesButton messages={messages} />
              <button
                className={`
                  text-sm sm:text-base
                  border border-gray-medium hover:border-gray-dark
                  hover:bg-gray-light opacity-70`}
                onClick={() => {
                  setOpenFeedback(true);
                }}
              >
                Feedback
              </button>
            </div>
          </>
        ) : (
          <InitializationForm
            addMessage={addMessage}
            setMessages={setMessages}
          />
        )}
      </div>
    </>
  );
}
