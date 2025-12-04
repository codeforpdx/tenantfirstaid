import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import useLocation, { ILocation } from "./hooks/useLocation";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useLetterContent } from "./hooks/useLetterContent";
import { streamText } from "./pages/Chat/utils/streamHelper";
import LetterGenerationDialog from "./pages/Letter/components/LetterGenerationDialog";
import { buildLetterUserMessage } from "./pages/Letter/utils/letterHelper";
import LetterDisclaimer from "./pages/Letter/components/LetterDisclaimer";
import MessageContainer from "./shared/components/MessageContainer";

export default function Letter() {
  const { addMessage, messages, setMessages } = useMessages();
  const { location, setLocation } = useLocation();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);
  const { org, loc } = useParams();
  const [startStreaming, setStartStreaming] = useState(false);
  const streamLocationRef = useRef<ILocation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const LOADING_DISPLAY_DELAY_MS = 1000;

  useEffect(() => {
    const output = buildLetterUserMessage(org, loc);
    if (output === null) return;

    const userMessageId = Date.now().toString();
    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: "user", content: output.userMessage, messageId: userMessageId },
    ]);
    streamLocationRef.current = output.selectedLocation;
    setStartStreaming(true);
  }, [loc, org, setMessages]);

  useEffect(() => {
    if (startStreaming === false || streamLocationRef.current === null) return;
    // Reset state to prevent re-running
    setStartStreaming(false);

    const runGenerateLetter = async () => {
      if (streamLocationRef.current !== null) {
        const streamDone = await streamText({
          addMessage,
          setMessages,
          location: streamLocationRef.current,
        });
        const INITIAL_INSTRUCTION =
          "What was generated is just an initial template. Please include details of your specific housing situation to update the letter.";
        const ERROR_MESSAGE =
          "Unable to generate letter. Please try again or refresh the page.";

        if (streamDone) {
          setMessages((prev) => [
            ...prev,
            {
              role: "model",
              content: INITIAL_INSTRUCTION,
              messageId: Date.now().toString(),
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: "model",
              content: ERROR_MESSAGE,
              messageId: Date.now().toString(),
            },
          ]);
        }
      }
    };

    runGenerateLetter();
  }, [startStreaming, addMessage, setMessages]);

  useEffect(() => {
    // Wait for the second message (index 1) which contains the initial AI response
    if (messages.length > 1 && messages[1]?.content !== "") {
      // Include 1s delay for smoother transition
      const timeoutId = setTimeout(
        () => setIsLoading(false),
        LOADING_DISPLAY_DELAY_MS,
      );
      return () => clearTimeout(timeoutId);
    }
  }, [messages]);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  return (
    <>
      <div className="absolute top-16 md:top-32 w-full flex items-center">
        <LetterGenerationDialog ref={dialogRef} />
        <div className="flex-1 h-full sm:h-auto items-center transition-all duration-300">
          <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
            <div
              className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"}`}
            >
              {isLoading ? (
                <div className="flex flex-1 items-center justify-center animate-pulse text-lg">
                  Generating letter...
                </div>
              ) : (
                <MessageWindow
                  messages={messages}
                  addMessage={addMessage}
                  location={location}
                  setLocation={setLocation}
                  setMessages={setMessages}
                  isOngoing={isOngoing}
                />
              )}
            </div>
          </MessageContainer>
          <LetterDisclaimer isOngoing={isOngoing} />
        </div>
      </div>
    </>
  );
}
