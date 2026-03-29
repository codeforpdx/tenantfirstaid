import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { HumanMessage } from "@langchain/core/messages";
import FeedbackModal from "../../pages/Chat/components/FeedbackModal";

vi.mock("../../pages/Chat/utils/feedbackHelper", () => ({
  default: vi.fn(),
}));

import sendFeedback from "../../pages/Chat/utils/feedbackHelper";

describe("FeedbackModal", () => {
  const messages = [new HumanMessage({ content: "hello", id: "1" })];

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("renders the feedback form in idle state", () => {
    render(<FeedbackModal messages={messages} setOpenFeedback={vi.fn()} />);

    expect(
      screen.getByPlaceholderText(/please enter your feedback/i),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter email/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/word.*to redact/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });

  it("calls setOpenFeedback(false) when Close is clicked", () => {
    const setOpenFeedback = vi.fn();
    render(
      <FeedbackModal messages={messages} setOpenFeedback={setOpenFeedback} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(setOpenFeedback).toHaveBeenCalledWith(false);
  });

  it("accepts input in all fields and passes them to sendFeedback on submit", () => {
    vi.useFakeTimers();
    render(<FeedbackModal messages={messages} setOpenFeedback={vi.fn()} />);

    fireEvent.change(
      screen.getByPlaceholderText(/please enter your feedback/i),
      {
        target: { value: "great bot" },
      },
    );
    fireEvent.change(screen.getByPlaceholderText(/enter email/i), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/word.*to redact/i), {
      target: { value: "landlord" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getByText("Feedback Sent!")).toBeInTheDocument();

    act(() => {
      vi.runAllTimers();
    });

    expect(sendFeedback).toHaveBeenCalledWith(
      messages,
      "great bot",
      "user@example.com",
      "landlord",
    );
  });

  it("closes immediately when Send is clicked with empty feedback", () => {
    const setOpenFeedback = vi.fn();
    render(
      <FeedbackModal messages={messages} setOpenFeedback={setOpenFeedback} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(setOpenFeedback).toHaveBeenCalledWith(false);
  });
});
