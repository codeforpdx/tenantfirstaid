import { useState } from "react";
import MessageWindow from "./pages/Chat/components/MessageWindow";
import StatuteDrawer from "./pages/Chat/components/StatuteDrawer";
import useMessages from "./hooks/useMessages";

export default function Chat() {
  const { messages, setMessages, isLoading, isError } = useMessages();
  const isOngoing = messages.length > 0;
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedStatute, setSelectedStatute] = useState<string | null>(null);

  const handleStatuteClick = (statute: string) => {
    if (statute === selectedStatute && drawerOpen) {
      closeDrawer();
    } else {
      setSelectedStatute(statute);
      setDrawerOpen(true);
    }
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedStatute(null);
  };

  return (
    <div className="h-dvh pt-16 flex items-center">
      <div className="flex w-full items-center ">
        <div className="flex-1 transition-all duration-300">
          <div
            className={`container relative flex flex-col mx-auto p-6 bg-[#F4F4F2] rounded-lg shadow-[0_4px_6px_rgba(0,0,0,0.1)]
              ${
                isOngoing
                  ? "justify-between h-[calc(100dvh-4rem-64px)] max-h-[calc(100dvh-4rem-64px)] sm:h-[calc(100dvh-10rem-64px)]"
                  : "justify-center max-w-[600px]"
              }`}
          >
            {isLoading ? (
              <div
                className={`${isLoading && "animate-dot-pulse"} text-center`}
              >
                Loading...
              </div>
            ) : (
              <MessageWindow
                messages={messages}
                setMessages={setMessages}
                isOngoing={isOngoing}
                isError={isError}
                onStatuteClick={handleStatuteClick}
              />
            )}
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
        <StatuteDrawer
          open={drawerOpen}
          statute={selectedStatute}
          onClose={closeDrawer}
        />
      </div>
    </div>
  );
}
