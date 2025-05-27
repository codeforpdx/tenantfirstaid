import { useState } from "react";
import { Link } from "react-router-dom";
import ExportMessagesButton from "./pages/Chat/components/ExportMessagesButton";
import MessageWindow from "./pages/Chat/components/MessageWindow";

export interface IMessage {
  role: "user" | "assistant";
  content: string;
  messageId: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<IMessage[]>([]);
  const isOngoing = messages.length > 0;

  return (
    <div className="h-dvh flex items-center">
      <ExportMessagesButton messages={messages} />
      <div
        className={`container relative flex flex-col mx-auto p-6 bg-white rounded-lg shadow-[0_4px_6px_rgba(0,0,0,0.1)]
          ${
            isOngoing
              ? "justify-between h-[calc(100dvh-10rem)]"
              : "justify-center max-w-[600px]"
          }`}
      >
        <MessageWindow
          messages={messages}
          setMessages={setMessages}
          isOngoing={isOngoing}
        />
      </div>
      <Link
        className="fixed bottom-6 right-[8vw] px-6 py-1.5 bg-white border border-[#4a90e2] text-[#4a90e2] hover:bg-[#4a90e2] hover:text-white rounded-full shadow-lg font-semibold transition-colors duration-300 cursor-pointer z-50"
        to="/about"
        title="About Us"
      >
        About Tenant First Aid
      </Link>
    </div>
  );
}
