import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import useLocation from "./hooks/useLocation";
import { useEffect, useState } from "react";
import DOMPurify, { SANITIZE_SETTINGS } from "./shared/utils/dompurify";

export default function Chat() {
  const { addMessage, messages, setMessages } = useMessages();
  const { location, setLocation } = useLocation();
  const isOngoing = messages.length > 0;
  const [letterContent, setLetterContent] = useState("");

  useEffect(() => {
    const messageLetters = messages?.filter(
      (message) =>
        message.content.split("-----generate letter-----").length === 2,
    );
    const latestLetter = messageLetters[messageLetters.length - 1];
    if (latestLetter) {
      setLetterContent(
        DOMPurify.sanitize(latestLetter?.content, SANITIZE_SETTINGS)
          .split("-----generate letter-----")[1]
          .trim(),
      );
    }
  }, [messages]);

  return (
    <div className="h-dvh pt-16 flex items-center">
      <div className="flex w-full items-center ">
        <div className="flex-1 transition-all duration-300">
          <div
            className={`container relative flex flex-col sm:flex-row gap-4 mx-auto p-6 bg-[#F4F4F2] rounded-lg shadow-[0_4px_6px_rgba(0,0,0,0.1)]
              ${
                isOngoing
                  ? "justify-between h-[calc(100dvh-4rem-64px)] max-h-[calc(100dvh-4rem-64px)] sm:h-[calc(100dvh-10rem-64px)]"
                  : "justify-center max-w-[600px]"
              }`}
          >
            {letterContent !== "" ? (
              <div className="flex flex-col gap-4 items-center flex-2/3 h-[40%] sm:h-full">
                <div className="overflow-y-scroll pr-4">
                  <span
                    className="whitespace-pre-wrap generated-letter"
                    dangerouslySetInnerHTML={{
                      __html: letterContent
                        .split("-----generate letter-----")[0]
                        .trim(),
                    }}
                  />
                </div>
              </div>
            ) : null}
            <div
              className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"} h-[60%] sm:h-full`}
            >
              <MessageWindow
                messages={messages}
                addMessage={addMessage}
                location={location}
                setLocation={setLocation}
                setMessages={setMessages}
                isOngoing={isOngoing}
              />
            </div>
          </div>
          <div
            className={`container mx-auto text-xs px-4 text-center ${isOngoing ? "max-w-auto my-2" : "max-w-[600px] my-4"}`}
          >
            <p className={`${isOngoing ? "mb-0" : "mb-2"}`}>
              {isOngoing
                ? "This chatbot offers general housing law info and is not legal advice. For help with your situation, contact a lawyer."
                : "The information provided by this chatbot is general information only and does not constitute legal advice. While Tenant First Aid strives to keep the content accurate and up to date,  completeness and accuracy is not guaranteed. If you have a specific legal issue or question, consider contacting a qualified attorney or a local legal aid clinic for personalized assistance."}
            </p>
            <p>For questions, contact michael@qiu-qiulaw.com</p>
          </div>
        </div>
      </div>
    </div>
  );
}
