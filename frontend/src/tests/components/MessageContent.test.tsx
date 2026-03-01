import { render, screen } from "@testing-library/react";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { describe, it, expect } from "vitest";
import MessageContent from "../../pages/Chat/components/MessageContent";
import type { TUiMessage } from "../../hooks/useMessages";

describe("MessageContent", () => {
  it("renders text chunk for AI message", () => {
    const message = new AIMessage({
      content: '{"type":"text","content":"Hello, this is the answer."}\n',
      id: "1",
    });
    render(<MessageContent message={message} />);
    expect(screen.getByText("Hello, this is the answer.")).toBeInTheDocument();
  });

  it("renders reasoning chunk with thinking icon", () => {
    const message = new AIMessage({
      content: '{"type":"reasoning","content":"I need to think about this."}\n',
      id: "2",
    });
    render(<MessageContent message={message} />);
    expect(screen.getByText("I need to think about this.")).toBeInTheDocument();
    expect(screen.getByText("🤔")).toBeInTheDocument();
  });

  it("renders both reasoning and text chunks when mixed", () => {
    const message = new AIMessage({
      content:
        '{"type":"reasoning","content":"Let me check the statute."}\n{"type":"text","content":"ORS 90.427 covers this."}\n',
      id: "3",
    });
    render(<MessageContent message={message} />);
    expect(screen.getByText("Let me check the statute.")).toBeInTheDocument();
    expect(screen.getByText("ORS 90.427 covers this.")).toBeInTheDocument();
    expect(screen.getByText("🤔")).toBeInTheDocument();
  });

  it("does not render letter chunk inline", () => {
    const message = new AIMessage({
      content: '{"type":"letter","content":"Dear Landlord, fix the heat."}\n',
      id: "4",
    });
    const { container } = render(<MessageContent message={message} />);
    expect(container.textContent).not.toContain("Dear Landlord");
  });

  it("shows Thinking... when AI message content is empty", () => {
    const message = new AIMessage({ content: "", id: "4" });
    render(<MessageContent message={message} />);
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });

  it("does not show Thinking... when message has only a reasoning chunk", () => {
    const message = new AIMessage({
      content: '{"type":"reasoning","content":"Let me think."}\n',
      id: "5",
    });
    render(<MessageContent message={message} />);
    expect(screen.queryByText("Thinking...")).toBeNull();
  });

  it("renders ui message as plain italic text without a label", () => {
    const message: TUiMessage = {
      type: "ui",
      text: "What was generated is just an initial template.",
      id: "6",
    };
    render(<MessageContent message={message} />);
    expect(
      screen.getByText("What was generated is just an initial template."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/You:/)).toBeNull();
    expect(screen.queryByText(/Brainy:/)).toBeNull();
  });

  it("renders human message as plain markdown without JSON parsing", () => {
    const message = new HumanMessage({
      content: "Is my landlord allowed to do this?",
      id: "5",
    });
    render(<MessageContent message={message} />);
    expect(
      screen.getByText("Is my landlord allowed to do this?"),
    ).toBeInTheDocument();
  });
});
