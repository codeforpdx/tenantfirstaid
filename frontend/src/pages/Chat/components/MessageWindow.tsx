import { useEffect, useRef, useState } from "react";
import type { IMessage } from "../../../hooks/useMessages";
import InputField from "./InputField";
import MessageContent from "./MessageContent";
import useSession from "../../../hooks/useSession";
import ExportMessagesButton from "./ExportMessagesButton";
import CitySelectField from "./CitySelectField";
import SuggestedPrompts from "./SuggestedPrompts";
import FeedbackModal from "./FeedbackModal";

const tabs = [
  { id: 0, title: "Chat" },
  { id: 1, title: "Create Letter" },
];

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
  const [openFeedback, setOpenFeedback] = useState(false);
  const [tabWidth, setTabWidth] = useState(0);
  const [currentTab, setCurrentTab] = useState(0);
  const { handleNewSession } = useSession();
  const tabRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  const handleTabsWidth = () => {
    if (tabRef.current !== null) {
      const parentWidth = tabRef.current.getBoundingClientRect().width;
      const numberOfTabs = tabs.length;
      const newTabWidth = parentWidth / numberOfTabs;
      setTabWidth(newTabWidth);
    }
  };

  useEffect(() => {
    const resizeObserver = new ResizeObserver(handleTabsWidth);
    const tabComponent = tabRef.current;

    if (tabComponent !== null) {
      resizeObserver.observe(tabComponent);
    }

    return () => {
      if (tabComponent !== null) {
        resizeObserver.unobserve(tabComponent);
      }
    };
  }, []);

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
        className={`flex-1 ${
          isOngoing ? "overflow-y-scroll" : "overflow-y-none"
        }`}
        ref={messagesRef}
      >
        {isError ? (
          <div className="flex items-center justify-center h-full text-center">
            Error fetching chat history. Try refreshing...
          </div>
        ) : (
          <div className="max-h-[calc(100dvh-240px)] sm:max-h-[calc(100dvh-20rem)] mx-auto max-w-[700px]">
            <div
              className="items-center justify-center mx-auto w-[280px] mb-4 bg-gray-200 rounded-full relative"
              style={{ display: isOngoing ? "flex" : "none" }}
              ref={tabRef}
            >
              {tabs.map((tab, index) => {
                return (
                  <button
                    className="py-1 text-sm relative cursor-pointer"
                    style={{ width: tabWidth * tabs.length }}
                    key={index}
                    onClick={() => {
                      setCurrentTab(tab.id);
                    }}
                  >
                    {tab.title}
                  </button>
                );
              })}
              <div
                className="bg-white inset-0 absolute rounded-full mix-blend-exclusion transition-all duration-300"
                style={{
                  width: tabWidth,
                  translate: `${currentTab * tabWidth}px`,
                }}
              />
            </div>
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
      {openFeedback && (
        <FeedbackModal messages={messages} setOpenFeedback={setOpenFeedback} />
      )}
      <div>
        {messages.length > 0 ? (
          <>
            {messages.length === 1 && inputValue === "" && (
              <SuggestedPrompts onPromptClick={handlePromptClick} />
            )}
            <InputField
              mode={currentTab}
              setCurrentTab={setCurrentTab}
              messages={messages}
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
              <ExportMessagesButton messages={messages} />
              <button
                className="py-2 px-4 border rounded-md font-semibold hover:bg-gray-200 transition-colors cursor-pointer opacity-70"
                onClick={() => {
                  setOpenFeedback(true);
                }}
              >
                Feedback
              </button>
            </div>
          </>
        ) : (
          <CitySelectField setMessages={setMessages} />
        )}
      </div>
    </>
  );
}
