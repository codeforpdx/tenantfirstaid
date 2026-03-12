import type { AIMessage, HumanMessage } from "@langchain/core/messages";

/**
 * Chat message Type aligned with LangChain's message types
 * to ensure consistency with backend.
 */
export type ChatMessage = HumanMessage | AIMessage | UiMessage;

/** UI-only message for display purposes; excluded from backend history. */
export type UiMessage = {
  type: "ui";
  text: string;
  id: string;
};
