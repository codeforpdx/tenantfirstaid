import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import MessageWindow from "../../pages/Chat/components/MessageWindow";
import { TChatMessage } from "../../hooks/useMessages";
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
  const messages: TChatMessage[] = [
    new HumanMessage({ content: "first message", id: "1" }),
    new AIMessage({
      content: '{"type":"text","content":"second message"}\n',
      id: "2",
    }),
    new HumanMessage({ content: "third message", id: "3" }),
  ];

  const defaultProps = {
    messages,
    addMessage: vi.fn(),
    setMessages: vi.fn(),
    isOngoing: true,
  };

  it("hides first 2 messages on letter page", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/letter/some-org"]}>
            <MessageWindow {...defaultProps} />
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
});
