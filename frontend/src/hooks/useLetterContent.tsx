import { useEffect, useState } from "react";
import { AIMessage } from "@langchain/core/messages";
import { TChatMessage } from "./useMessages";
import DOMPurify, { SANITIZE_AI_SETTINGS } from "../shared/utils/dompurify";

const LETTER_START = "-----generate letter-----";
const LETTER_END = "-----end of letter-----";

function extractLetter(content: string) {
  const startIndex = content.lastIndexOf(LETTER_START);
  const endIndex = content.indexOf(LETTER_END, startIndex);

  if (startIndex === -1 || endIndex === -1) {
    return { letter: null, reconstructedContent: content };
  }

  const letter = content
    .substring(startIndex + LETTER_START.length, endIndex)
    .trim();

  const before = content.substring(0, startIndex).trim();
  const after = content.substring(endIndex + LETTER_END.length).trim();
  const reconstructedContent = [before, after]
    .filter(Boolean)
    .map((text) => text.replace(/`/g, "'"))
    .join("\n\n");

  return { letter, reconstructedContent };
}

/**
 * Extracts and sanitizes generated letter content from chat messages.
 * Strips the letter block from the message and returns it separately.
 */
export function useLetterContent(
  messages: TChatMessage[],
  setMessages: React.Dispatch<React.SetStateAction<TChatMessage[]>>,
) {
  const [letterContent, setLetterContent] = useState("");

  useEffect(() => {
    const messagesWithLetter = messages.filter((message) =>
      message.text.includes(LETTER_START),
    );
    const latestMessageWithLetter =
      messagesWithLetter[messagesWithLetter.length - 1];

    if (latestMessageWithLetter === undefined) return;

    const { letter, reconstructedContent } = extractLetter(
      latestMessageWithLetter.text,
    );

    if (letter === null) return;

    setLetterContent(DOMPurify.sanitize(letter, SANITIZE_AI_SETTINGS));
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === latestMessageWithLetter.id
          ? new AIMessage({
              content: DOMPurify.sanitize(
                reconstructedContent,
                SANITIZE_AI_SETTINGS,
              ),
              id: msg.id,
            })
          : msg,
      ),
    );
  }, [messages, setMessages]);

  return { letterContent };
}
