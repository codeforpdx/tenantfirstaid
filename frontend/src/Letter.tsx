import { HumanMessage } from "@langchain/core/messages";
import type { TUiMessage } from "./hooks/useMessages";
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
import clsx from "clsx";

export default function Letter() {
  const { addMessage, messages, setMessages } = useMessages();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);
  const { org, loc } = useParams();
  const [startStreaming, setStartStreaming] = useState(false);
  const streamLocationRef = useRef<ILocation | null>(null);
  const [isGenerating, setIsGenerating] = useState(true);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasInitialized = useRef(false);
  const LOADING_DISPLAY_DELAY_MS = 1000;
  const { housingLocation, housingType, tenantTopic, issueDescription } =
    useHousingContext();
  const { userMessage: initialUserMessage } = buildChatUserMessage(
    housingLocation,
    housingType,
    tenantTopic,
    issueDescription,
  );

  // Adds the initial user message once and triggers streaming.
  useEffect(() => {
    if (hasInitialized.current) return;
    const output = buildLetterUserMessage(org, loc);
    if (output === null) return;
    hasInitialized.current = true;
    const hasIssueContext = issueDescription !== "";

    const userMessageId = Date.now().toString();
    // Add user message
    setMessages((prev) => [
      ...prev,
      new HumanMessage({
        content: [hasIssueContext ? initialUserMessage : "", output.userMessage]
          .join(" ")
          .trim(),
        id: userMessageId,
      }),
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

        const text = streamDone ? INITIAL_INSTRUCTION : ERROR_MESSAGE;
        const uiMessage: TUiMessage = {
          type: "ui",
          text,
          id: Date.now().toString(),
        };
        setMessages((prev) => [...prev, uiMessage]);
        // Clear spinner after a short delay for a smoother transition.
        timerRef.current = setTimeout(
          () => setIsGenerating(false),
          LOADING_DISPLAY_DELAY_MS,
        );
      }
    };

    runGenerateLetter();
  }, [startStreaming, addMessage, setMessages]);

  // Clear any pending timer if the component unmounts before it fires.
  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  return (
    <>
      <LetterGenerationDialog ref={dialogRef} />
      <div className="h-full w-full flex flex-col lg:flex-row gap-4 transition-all duration-300 sm:px-4 max-w-[1400px]">
        <div className="my-auto w-full flex">
          <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
            <div
              className={clsx(
                "flex flex-col min-h-0",
                letterContent === "" ? "flex-1" : "flex-1/3",
              )}
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
        <div
          className={clsx(
            "flex flex-col m-auto w-full rounded-lg bg-paper-background",
            "lg:self-start lg:max-w-[300px]",
            "[@media(max-height:800px)]:my-0 [@media(max-height:800px)]:self-stretch [@media(max-height:800px)]:overflow-hidden",
          )}
        >
          <div className="[@media(max-height:800px)]:overflow-y-auto">
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
