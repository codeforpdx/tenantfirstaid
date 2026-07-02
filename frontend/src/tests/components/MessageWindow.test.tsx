import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import MessageWindow from "../../pages/Chat/components/MessageWindow";
import type { ChatMessage } from "../../shared/types/messages";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HousingContextProvider from "../../contexts/HousingContext";

beforeAll(() => {
  if (!("scrollTo" in HTMLElement.prototype)) {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    HTMLElement.prototype.scrollTo = function () {};
  }
});

describe("MessageWindow component", () => {
  const messages: ChatMessage[] = [
    new HumanMessage({ content: "first message", id: "1" }),
    new AIMessage({
      content: '{"type":"text","content":"second message"}\n',
      id: "2",
    }),
    new HumanMessage({ content: "third message", id: "3" }),
  ];

  const defaultProps = {
    mode: "chat" as const,
    messages,
    addMessage: vi.fn(),
    setMessages: vi.fn(),
    isOngoing: true,
    clearMessages: vi.fn(),
  };

  it("hides first 2 messages on letter page", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/letter/some-org"]}>
            <MessageWindow {...defaultProps} mode="letter" />
          </MemoryRouter>
        </HousingContextProvider>
      </QueryClientProvider>,
    );

    expect(screen.queryByText("first message")).toBeNull();
    expect(screen.queryByText("second message")).toBeNull();
    expect(screen.getByText("third message")).toBeInTheDocument();
  });

  it("shows all messages on non-letter pages", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/chat"]}>
            <MessageWindow {...defaultProps} />
          </MemoryRouter>
        </HousingContextProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText("first message")).toBeInTheDocument();
    expect(screen.getByText("second message")).toBeInTheDocument();
    expect(screen.getByText("third message")).toBeInTheDocument();
  });

  it("does not show the chat initialization form for an empty letter", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/letter/or/portland"]}>
            <MessageWindow
              {...defaultProps}
              mode="letter"
              messages={[]}
              isOngoing={false}
            />
          </MemoryRouter>
        </HousingContextProvider>
      </QueryClientProvider>,
    );

    expect(screen.queryByText("Welcome to Tenant First Aid!")).toBeNull();
  });

  it("shows the chat initialization form for an empty chat", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/chat/or/portland"]}>
            <MessageWindow
              {...defaultProps}
              messages={[]}
              isOngoing={false}
            />
          </MemoryRouter>
        </HousingContextProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText("Welcome to Tenant First Aid!")).toBeInTheDocument();
  });

  it("delegates clearing to the provided callback", () => {
    const clearMessages = vi.fn();
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/chat/or/portland"]}>
            <MessageWindow
              {...defaultProps}
              clearMessages={clearMessages}
            />
          </MemoryRouter>
        </HousingContextProvider>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "clear chat" }));

    expect(clearMessages).toHaveBeenCalledTimes(1);
  });
});
