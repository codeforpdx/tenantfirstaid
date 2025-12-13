import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import { useLetterContent } from "./hooks/useLetterContent";
import ChatDisclaimer from "./pages/Chat/components/ChatDisclaimer";
import MessageContainer from "./shared/components/MessageContainer";
import FeatureSnippet from "./shared/components/FeatureSnippet";

export default function Chat() {
  const { addMessage, messages, setMessages } = useMessages();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);

  return (
    <div className="flex pt-16 h-screen items-center justify-center">
      <div className="h-full w-full flex flex-col lg:flex-row gap-4 transition-all duration-300 md:px-4 max-w-[1400px]">
        <div className="my-auto w-full flex">
          <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
            <div
              className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"}`}
            >
              <MessageWindow
                messages={messages}
                addMessage={addMessage}
                setMessages={setMessages}
                isOngoing={isOngoing}
              />
            </div>
          </MessageContainer>
        </div>
        <div className="flex flex-col m-auto lg:h-[620px] lg:max-w-[300px] rounded-lg bg-paper-background">
          <FeatureSnippet />
          <div className="p-4">
            <ChatDisclaimer isOngoing={isOngoing} />
          </div>
        </div>
      </div>
    </div>
  );
}
