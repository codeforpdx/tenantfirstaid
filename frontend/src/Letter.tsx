import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useLetterContent } from "./hooks/useLetterContent";
import { streamText } from "./pages/Chat/utils/streamHelper";
import LetterGenerationDialog from "./pages/Letter/components/LetterGenerationDialog";
import { buildLetterUserMessage } from "./pages/Letter/utils/letterHelper";
import LetterDisclaimer from "./pages/Letter/components/LetterDisclaimer";
import MessageContainer from "./shared/components/MessageContainer";
import useHousingContext from "./hooks/useHousingContext";
import { buildChatUserMessage } from "./pages/Chat/utils/formHelper";
import { ILocation } from "./contexts/HousingContext";
import FeatureSnippet from "./shared/components/FeatureSnippet";

export default function Letter() {
  const { addMessage, messages, setMessages } = useMessages();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);
  const { org, loc } = useParams();
  const [startStreaming, setStartStreaming] = useState(false);
  const streamLocationRef = useRef<ILocation | null>(null);
  const [isGenerating, setIsGenerating] = useState(true);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const LOADING_DISPLAY_DELAY_MS = 1000;
  const { housingLocation, housingType, tenantTopic, issueDescription } =
    useHousingContext();
  const { userMessage: initialUserMessage } = buildChatUserMessage(
    housingLocation,
    housingType,
    tenantTopic,
    issueDescription,
  );

  useEffect(() => {
    const output = buildLetterUserMessage(org, loc);
    if (output === null) return;
    const hasIssueContext = issueDescription !== "";

    const userMessageId = Date.now().toString();
    // Add user message
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: [hasIssueContext ? initialUserMessage : "", output.userMessage]
          .join(" ")
          .trim(),
        messageId: userMessageId,
      },
    ]);
    streamLocationRef.current = output.selectedLocation;
    setStartStreaming(true);
  }, [loc, org, setMessages, issueDescription, initialUserMessage]);

  useEffect(() => {
    if (startStreaming === false || streamLocationRef.current === null) return;
    // Reset state to prevent re-running
    setStartStreaming(false);

    const runGenerateLetter = async () => {
      if (streamLocationRef.current !== null) {
        const streamDone = await streamText({
          addMessage,
          setMessages,
          housingLocation: streamLocationRef.current,
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
        () => setIsGenerating(false),
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
      <div className="flex pt-16 h-screen items-center justify-center">
        <LetterGenerationDialog ref={dialogRef} />
        <div className="h-full w-full flex flex-col lg:flex-row gap-4 transition-all duration-300 sm:px-4 max-w-[1400px]">
          <div className="my-auto w-full flex">
            <MessageContainer
              isOngoing={isOngoing}
              letterContent={letterContent}
            >
              <div
                className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"}`}
              >
                {isGenerating ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="animate-pulse text-lg">
                      Generating Letter...
                    </div>
                  </div>
                ) : (
                  <MessageWindow
                    messages={messages}
                    addMessage={addMessage}
                    setMessages={setMessages}
                    isOngoing={isOngoing}
                  />
                )}
              </div>
            </MessageContainer>
          </div>
          <div className="flex flex-col m-auto lg:h-[620px] lg:max-w-[300px] rounded-lg bg-paper-background">
            <FeatureSnippet />
            <div className="p-4">
              <LetterDisclaimer isOngoing={isOngoing} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
