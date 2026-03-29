import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi, beforeAll } from "vitest";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import MessageWindow from "../../pages/Chat/components/MessageWindow";
import type { ChatMessage } from "../../shared/types/messages";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HousingContextProvider from "../../contexts/HousingContext";

vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: vi.fn(),
}));

function renderMessageWindow(
  props: Partial<React.ComponentProps<typeof MessageWindow>> = {},
  path = "/chat",
) {
  const queryClient = new QueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <MemoryRouter initialEntries={[path]}>
          <MessageWindow
            messages={[]}
            addMessage={vi.fn()}
            setMessages={vi.fn()}
            isOngoing={false}
            {...props}
          />
        </MemoryRouter>
      </HousingContextProvider>
    </QueryClientProvider>,
  );
}

const messages: ChatMessage[] = [
  new HumanMessage({ content: "first message", id: "1" }),
  new AIMessage({
    content: '{"type":"text","content":"second message"}\n',
    id: "2",
  }),
  new HumanMessage({ content: "third message", id: "3" }),
];

describe("MessageWindow component", () => {
  beforeAll(() => {
    if (!("scrollTo" in HTMLElement.prototype)) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      HTMLElement.prototype.scrollTo = function () {};
    }
  });

  it("hides first 2 messages on letter page", () => {
    renderMessageWindow({ messages, isOngoing: true }, "/letter/some-org");

    expect(screen.queryByText("first message")).toBeNull();
    expect(screen.queryByText("second message")).toBeNull();
    expect(screen.getByText("third message")).toBeInTheDocument();
  });

  it("shows all messages on non-letter pages", () => {
    renderMessageWindow({ messages, isOngoing: true });

    expect(screen.getByText("first message")).toBeInTheDocument();
    expect(screen.getByText("second message")).toBeInTheDocument();
    expect(screen.getByText("third message")).toBeInTheDocument();
  });

  it("shows initialization form when there are no messages", () => {
    renderMessageWindow({ messages: [], isOngoing: false });

    expect(
      screen.getByRole("button", { name: "enter chat" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Send" }),
    ).not.toBeInTheDocument();
  });

  it("shows InputField and action buttons when messages exist", () => {
    renderMessageWindow({ messages, isOngoing: true });

    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "clear chat" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Feedback" }),
    ).toBeInTheDocument();
  });

  it("opens FeedbackModal when Feedback button is clicked", () => {
    renderMessageWindow({ messages, isOngoing: true });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Feedback" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
