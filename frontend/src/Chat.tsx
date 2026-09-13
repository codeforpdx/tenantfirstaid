import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages, { CHAT_MESSAGES_STORAGE_PREFIX } from "./hooks/useMessages";
import useSyncJurisdiction from "./hooks/useSyncJurisdiction";
import { useLetterContent } from "./hooks/useLetterContent";
import ChatDisclaimer from "./pages/Chat/components/ChatDisclaimer";
import FrequentInquiries from "./shared/components/FrequentInquiries";
import MessageContainer from "./shared/components/MessageContainer";
import FeaturesPanel from "./shared/components/FeaturesPanel";
import MobilePanel from "./shared/components/MobilePanel";
import { Navigate, useParams } from "react-router-dom";
import {
  classifyStateSegment,
  pathFor,
  resolveJurisdiction,
} from "./shared/utils/jurisdiction";
import { DEFAULT_JURISDICTION } from "./shared/constants/jurisdictions";
import clsx from "clsx";
import { useDevicePrivacy } from "./contexts/DevicePrivacyContext";
import { useEffect, useRef } from "react";

/**
 * Routes /chat requests by classifying the :state segment: an out-of-state
 * state is redirected to Oregon with a flag so the page can explain the
 * switch, a non-state typo is quietly canonicalized to Oregon, and supported
 * states render ChatView.
 */
export default function Chat() {
  const { state: stateParam, city: cityParam } = useParams();
  const kind = classifyStateSegment(stateParam);

  if (kind === "out-of-state") {
    return (
      <Navigate
        to={pathFor("chat", DEFAULT_JURISDICTION)}
        replace
        state={{ unsupportedRegion: true }}
      />
    );
  }

  if (kind === "unknown") {
    return <Navigate to={pathFor("chat", DEFAULT_JURISDICTION)} replace />;
  }

  const jurisdiction = resolveJurisdiction(stateParam, cityParam);
  return <ChatView key={jurisdiction.key} />;
}

function ChatView() {
  useSyncJurisdiction();
  const { state, city } = useParams();
  const jurisdiction = resolveJurisdiction(state, city);
  const devicePrivacy = useDevicePrivacy();
  const { addMessage, messages, setMessages, clearMessages } = useMessages(
    devicePrivacy === "private"
      ? `${CHAT_MESSAGES_STORAGE_PREFIX}${jurisdiction.key}`
      : undefined,
  );
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);
  const hasCheckedRestoredMessages = useRef(false);

  useEffect(() => {
    if (hasCheckedRestoredMessages.current) return;
    hasCheckedRestoredMessages.current = true;
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.type !== "human") return;

    // Incomplete AI responses are not stored, leaving an unanswered question.
    setMessages((previous) => [
      ...previous,
      {
        type: "ui",
        text: "The response was interrupted. Please send your message again.",
        id: `interrupted-response:${lastMessage.id}`,
      },
    ]);
  }, [messages, setMessages]);

  return (
    <div className="min-h-full lg:h-full w-full flex flex-col lg:flex-row transition-all duration-300 lg:relative lg:bg-paper-background">
      <div className="flex-1 lg:my-0 w-full lg:flex-1 flex lg:order-2">
        <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
          <div
            className={clsx(
              "flex flex-col min-h-0",
              letterContent === "" ? "flex-1" : "flex-1/3",
              !isOngoing && "lg:overflow-y-auto",
            )}
          >
            <MessageWindow
              mode="chat"
              messages={messages}
              addMessage={addMessage}
              setMessages={setMessages}
              isOngoing={isOngoing}
              clearMessages={clearMessages}
            />
          </div>
        </MessageContainer>
      </div>
      <div
        className={clsx(
          "flex flex-col w-full bg-paper-background",
          "border-b lg:border-b-0 border-gray-light",
          "lg:order-1 lg:my-0 lg:w-1/5 lg:border-r",
          "[@media(max-height:800px)]:my-0 [@media(max-height:800px)]:self-stretch [@media(max-height:800px)]:overflow-hidden",
        )}
      >
        <MobilePanel title="Frequent Inquiries">
          <div className="flex-1 min-h-0 lg:overflow-y-auto [@media(max-height:800px)]:overflow-y-auto">
            <FrequentInquiries />
          </div>
        </MobilePanel>
      </div>
      <FeaturesPanel disclaimer={<ChatDisclaimer isOngoing={isOngoing} />} />
    </div>
  );
}
