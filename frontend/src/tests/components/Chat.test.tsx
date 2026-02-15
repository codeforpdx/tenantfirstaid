import { render, cleanup, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, afterEach, beforeAll } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { AIMessage, HumanMessage } from "@langchain/core/messages";

beforeAll(() => {
  if (!("scrollTo" in HTMLElement.prototype)) {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    HTMLElement.prototype.scrollTo = function () {};
  }
});

let mockUseMessagesReturn: object;

vi.mock("../../hooks/useMessages", () => ({
  default: () => mockUseMessagesReturn,
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: () => <div data-testid="message-window-stub" />,
}));

const mockMessages1 = [
  new AIMessage({ content: "some text", id: "1" }),
  new HumanMessage({ content: "some text", id: "2" }),
  new AIMessage({
    content:
      "some text-----generate letter-----<p>Letter HTML</p>-----end of letter-----",
    id: "3",
  }),
];

const mockMessages2 = [
  new AIMessage({ content: "some text", id: "1" }),
  new HumanMessage({ content: "some text", id: "2" }),
  new AIMessage({ content: "some text", id: "3" }),
];

const renderChat = async () => {
  const { default: Chat } = await import("../../Chat");
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Chat />
      </BrowserRouter>
    </QueryClientProvider>,
  );
};

describe("Chat generated-letter block", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders .generated-letter when a message contains the separator", async () => {
    mockUseMessagesReturn = {
      addMessage: vi.fn(),
      messages: mockMessages1,
      setMessages: vi.fn(),
    };

    await renderChat();

    await waitFor(() =>
      expect(document.querySelector(".generated-letter")).not.toBeNull(),
    );
  });

  it("does not render .generated-letter when no message contains the separator", async () => {
    mockUseMessagesReturn = {
      addMessage: vi.fn(),
      messages: mockMessages2,
      setMessages: vi.fn(),
    };

    await renderChat();

    await waitFor(() =>
      expect(document.querySelector(".generated-letter")).toBeNull(),
    );
  });
});
