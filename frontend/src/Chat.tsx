import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import useSyncJurisdiction from "./hooks/useSyncJurisdiction";
import { useLetterContent } from "./hooks/useLetterContent";
import ChatDisclaimer from "./pages/Chat/components/ChatDisclaimer";
import ChatPageLayout from "./layouts/ChatPageLayout";
import { Navigate, useParams } from "react-router-dom";
import { classifyStateSegment, pathFor } from "./shared/utils/jurisdiction";
import { DEFAULT_JURISDICTION } from "./shared/constants/jurisdictions";

/**
 * Routes /chat requests by classifying the :state segment: an out-of-state
 * state is redirected to Oregon with a flag so the page can explain the
 * switch, a non-state typo is quietly canonicalized to Oregon, and supported
 * states render ChatView.
 */
export default function Chat() {
  const { state: stateParam } = useParams();
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

  return <ChatView />;
}

function ChatView() {
  useSyncJurisdiction();
  const { addMessage, messages, setMessages } = useMessages();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);

  return (
    <ChatPageLayout
      isOngoing={isOngoing}
      letterContent={letterContent}
      disclaimer={<ChatDisclaimer isOngoing={isOngoing} />}
    >
      <MessageWindow
        messages={messages}
        addMessage={addMessage}
        setMessages={setMessages}
        isOngoing={isOngoing}
      />
    </ChatPageLayout>
  );
}
