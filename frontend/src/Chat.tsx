import ExportMessagesButton from "./pages/Chat/components/ExportMessagesButton";
import { useNavigate } from "react-router-dom";
import MessageWindow from "./pages/Chat/components/MessageWindow";
import { useState } from "react";

export interface IMessage {
  role: "user" | "assistant";
  content: string;
  messageId: string;
  showFeedback?: boolean;
  feedbackSubmitted?: boolean;
}

export default function Chat() {
  const [messages, setMessages] = useState<IMessage[]>([]);
  const isOngoing = messages.length > 0;

  const navigate = useNavigate();

  return (
    <div className="h-screen flex items-center">
      <div
        className={`container relative flex flex-col my-20 mx-auto p-6 bg-white rounded-lg shadow-[0_4px_6px_rgba(0,0,0,0.1)]
          ${
            isOngoing
              ? "justify-between h-[calc(100vh-10rem)]"
              : "justify-center max-w-[600px]"
          }`}
      >
        <ExportMessagesButton messages={messages} />
        <MessageWindow
          messages={messages}
          setMessages={setMessages}
          isOngoing={isOngoing}
        />
        <button
          className="fixed bottom-6 right-1/4 translate-x-1/2 sm:right-8 sm:translate-x-0 bg-white border border-[#4a90e2] text-[#4a90e2] hover:bg-[#4a90e2] hover:text-white rounded-full shadow-lg px-6 py-3 font-semibold transition-colors duration-300 cursor-pointer z-50"
          onClick={() => navigate("/about")}
          title="About Us"
        >
          About Tenant First Aid
        </button>
      </div>
    </div>
  );
}
