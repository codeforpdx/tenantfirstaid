import { useEffect, useState } from "react";
import { IMessage } from "./useMessages";
import DOMPurify, { SANITIZE_AI_SETTINGS } from "../shared/utils/dompurify";

export function useLetterContent(messages: IMessage[]) {
  const [letterContent, setLetterContent] = useState("");

  useEffect(() => {
    const messageLetters = messages?.filter(
      (message) =>
        message.content.split("-----generate letter-----").length === 2,
    );
    const latestLetter = messageLetters[messageLetters.length - 1];
    if (latestLetter) {
      setLetterContent(
        DOMPurify.sanitize(latestLetter?.content, SANITIZE_AI_SETTINGS)
          .split("-----generate letter-----")[1]
          .trim(),
      );
    }
  }, [messages]);

  return { letterContent };
}
