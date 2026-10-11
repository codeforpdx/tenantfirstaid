import { HumanMessage } from "@langchain/core/messages";
import type { UiMessage } from "./shared/types/messages";
import MessageWindow from "./pages/Chat/components/MessageWindow";
import useMessages from "./hooks/useMessages";
import { useEffect, useRef, useState } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import { useLetterContent } from "./hooks/useLetterContent";
import { streamText } from "./pages/Chat/utils/streamHelper";
import LetterGenerationDialog from "./pages/Letter/components/LetterGenerationDialog";
import {
  buildLetterUserMessage,
  sanitizeOrg,
} from "./pages/Letter/utils/letterHelper";
import {
  classifyStateSegment,
  pathFor,
  jurisdictionByKey,
  resolveJurisdiction,
  toLocation,
} from "./shared/utils/jurisdiction";
import {
  DEFAULT_JURISDICTION,
  type JurisdictionOption,
} from "./shared/constants/jurisdictions";
import LetterDisclaimer from "./pages/Letter/components/LetterDisclaimer";
import useHousingContext from "./hooks/useHousingContext";
import ChatPageLayout from "./layouts/ChatPageLayout";
import { buildLocationPrefix } from "./shared/utils/buildLocationPrefix";
import { createId } from "./shared/utils/createId";

/**
 * Routes /letter requests by classifying the leading segment: an out-of-state
 * state is redirected to Oregon with a flag so the page can explain the switch,
 * a legacy /letter/:org/:loc partner link is redirected to the canonical
 * /letter/:state/:city?org= form, and supported states render LetterView.
 */
export default function Letter() {
  const { state: seg1, city: seg2 } = useParams();
  const [searchParams] = useSearchParams();
  const kind = classifyStateSegment(seg1);

  if (kind === "out-of-state") {
    return (
      <Navigate
        to={pathFor("letter", DEFAULT_JURISDICTION)}
        replace
        state={{ unsupportedRegion: true }}
      />
    );
  }

  // A non-state leading segment is a legacy /letter/:org/:loc partner link;
  // the loc shares the JurisdictionKey naming, so look it up directly.
  if (kind === "unknown") {
    const search = seg1 ? `?org=${encodeURIComponent(seg1)}` : "";
    return (
      <Navigate
        to={pathFor("letter", jurisdictionByKey(seg2), search)}
        replace
      />
    );
  }

  const jurisdiction = resolveJurisdiction(seg1, seg2);
  const org = searchParams.get("org") ?? undefined;
  // Remount on jurisdiction/org change so the letter regenerates from scratch
  // (the init guard and message state are per-mount).
  return (
    <LetterView
      key={`${jurisdiction.key}|${org ?? ""}`}
      jurisdiction={jurisdiction}
      org={org}
    />
  );
}

interface LetterViewProps {
  jurisdiction: JurisdictionOption;
  org: string | undefined;
}

function LetterView({ jurisdiction, org }: LetterViewProps) {
  const { addMessage, messages, setMessages } = useMessages();
  const isOngoing = messages.length > 0;
  const { letterContent } = useLetterContent(messages);
  const [isGenerating, setIsGenerating] = useState(true);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasInitialized = useRef(false);
  const LOADING_DISPLAY_DELAY_MS = 1000;
  const { issueDescription, handleHousingLocation, handleCityChange } =
    useHousingContext();

  // Keep the URL the source of truth for follow-up messages and the navbar
  // location picker on this page.
  useEffect(() => {
    handleHousingLocation(toLocation(jurisdiction));
    handleCityChange(jurisdiction.key);
  }, [jurisdiction, handleHousingLocation, handleCityChange]);

  // Adds the initial user message once and streams the letter.
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;
    const loc = toLocation(jurisdiction);
    const output = buildLetterUserMessage(org, loc);
    const content = [
      buildLocationPrefix(loc.city, loc.state),
      issueDescription,
      output.userMessage,
    ]
      .join(" ")
      .trim();
    const userMessage = new HumanMessage({
      content,
      id: createId(),
    });
    setMessages((prev) => [...prev, userMessage]);

    const runGenerateLetter = async () => {
      let cleanCompletion = false;
      await streamText({
        addMessage,
        history: [userMessage],
        setMessages,
        housingLocation: output.selectedLocation,
        onDone: () => {
          cleanCompletion = true;
          const uiMessage: UiMessage = {
            type: "ui",
            text: "What was generated is just an initial template. Please include details of your specific housing situation to update the letter.",
            id: createId(),
          };
          setMessages((prev) => [...prev, uiMessage]);
        },
      });
      // No done chunk received — surface an error instead of a silent empty panel.
      if (!cleanCompletion) {
        const uiMessage: UiMessage = {
          type: "ui",
          text: "Unable to generate letter. Please try again or refresh the page.",
          id: createId(),
        };
        setMessages((prev) => [...prev, uiMessage]);
      }
      // Clear spinner after a short delay for a smoother transition.
      timerRef.current = setTimeout(
        () => setIsGenerating(false),
        LOADING_DISPLAY_DELAY_MS,
      );
    };

    runGenerateLetter();
  }, [jurisdiction, org, addMessage, setMessages, issueDescription]);

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
      <LetterGenerationDialog
        ref={dialogRef}
        isRedirected={sanitizeOrg(org) !== ""}
      />
      <ChatPageLayout
        isOngoing={isOngoing}
        letterContent={letterContent}
        disclaimer={<LetterDisclaimer isOngoing={isOngoing} />}
      >
        {isGenerating ? (
          <div className="h-full flex items-center justify-center">
            <div className="animate-pulse text-lg">Generating Letter...</div>
          </div>
        ) : (
          <MessageWindow
            messages={messages}
            addMessage={addMessage}
            setMessages={setMessages}
            isOngoing={isOngoing}
            // Hide the initial prompt and the AI letter response.
            hiddenMessageCount={2}
          />
        )}
      </ChatPageLayout>
    </>
  );
}
