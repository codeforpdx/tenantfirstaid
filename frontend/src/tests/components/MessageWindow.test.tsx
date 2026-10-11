import { screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import MessageWindow from "../../pages/Chat/components/MessageWindow";
import type { ChatMessage } from "../../shared/types/messages";
import { createPendingReader, renderWithProviders } from "../testUtils";

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
    messages,
    addMessage: vi.fn(),
    setMessages: vi.fn(),
    isOngoing: true,
  };

  it("hides the leading messages given by hiddenMessageCount", () => {
    renderWithProviders(
      <MessageWindow {...defaultProps} hiddenMessageCount={2} />,
    );

    expect(screen.queryByText("first message")).toBeNull();
    expect(screen.queryByText("second message")).toBeNull();
    expect(screen.getByText("third message")).toBeInTheDocument();
  });

  it("shows all messages by default", () => {
    renderWithProviders(<MessageWindow {...defaultProps} />);

    expect(screen.getByText("first message")).toBeInTheDocument();
    expect(screen.getByText("second message")).toBeInTheDocument();
    expect(screen.getByText("third message")).toBeInTheDocument();
  });

  it("disables the chat input while the first response is streaming", async () => {
    const addMessage = vi.fn().mockResolvedValue(createPendingReader());

    function Harness() {
      const [messages, setMessages] = useState<ChatMessage[]>([]);
      return (
        <MessageWindow
          messages={messages}
          addMessage={addMessage}
          setMessages={setMessages}
          isOngoing={messages.length > 0}
        />
      );
    }

    renderWithProviders(<Harness />, { route: "/chat" });

    fireEvent.change(
      screen.getByPlaceholderText(/briefly describe your specific/i),
      { target: { value: "My landlord won't fix the heat" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "enter chat" }));

    expect(
      await screen.findByPlaceholderText(/type your message here/i),
    ).toBeDisabled();
  });
});
