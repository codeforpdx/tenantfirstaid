import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import useLocation from "./hooks/useLocation";
import { useLetterContent } from "./hooks/useLetterContent";
import ChatDisclaimer from "./pages/Chat/components/ChatDisclaimer";
import MessageContainer from "./shared/components/MessageContainer";

export default function Chat() {
  const { addMessage, messages, setMessages } = useMessages();
  const { location, setLocation } = useLocation();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);

  return (
    // Chat layout is adjusted before and after session starts to account for CitySelectField
    <div
      className={`absolute ${isOngoing ? "top-16 md:top-32" : "top-1/2 -translate-y-1/2"} w-full flex items-center`}
    >
      <div className="flex-1 h-full sm:h-auto items-center transition-all duration-300">
        <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
          <div
            className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"}`}
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
        </MessageContainer>
        <ChatDisclaimer isOngoing={isOngoing} />
      </div>
    </div>
  );
}
