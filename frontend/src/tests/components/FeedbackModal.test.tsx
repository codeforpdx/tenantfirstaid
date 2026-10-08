import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import FeedbackModal from "../../pages/Chat/components/FeedbackModal";

const messages = [
  new HumanMessage({ content: "Hello", id: "1" }),
  new AIMessage({ content: "Hi", id: "2" }),
];

function renderModal(fetchImpl: () => Promise<unknown>) {
  const fetchSpy = vi.fn(fetchImpl);
  vi.stubGlobal("fetch", fetchSpy);
  const setOpenFeedback = vi.fn();
  render(
    <FeedbackModal messages={messages} setOpenFeedback={setOpenFeedback} />,
  );
  return { fetchSpy, setOpenFeedback };
}

function typeFeedbackAndSend(text: string) {
  fireEvent.change(screen.getByPlaceholderText(/enter your feedback/i), {
    target: { value: text },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

describe("FeedbackModal", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("closes without sending when feedback is empty", () => {
    const { fetchSpy, setOpenFeedback } = renderModal(() =>
      Promise.resolve({ ok: true }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(setOpenFeedback).toHaveBeenCalledWith(false);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("sends only once when Send is clicked twice", () => {
    const { fetchSpy } = renderModal(() => new Promise(() => {}));

    typeFeedbackAndSend("Helpful");
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("shows Sending… while the request is in flight", () => {
    renderModal(() => new Promise(() => {}));

    typeFeedbackAndSend("Helpful");

    expect(screen.getByText("Sending…")).toBeInTheDocument();
    expect(screen.queryByText("Feedback Sent!")).not.toBeInTheDocument();
  });

  it("shows Feedback Sent! after the server accepts it", async () => {
    renderModal(() => Promise.resolve({ ok: true }));

    typeFeedbackAndSend("Helpful");

    expect(await screen.findByText("Feedback Sent!")).toBeInTheDocument();
  });

  it("closes shortly after showing Feedback Sent!", async () => {
    vi.useFakeTimers();
    const { setOpenFeedback } = renderModal(() =>
      Promise.resolve({ ok: true }),
    );

    typeFeedbackAndSend("Helpful");
    await act(async () => {});

    expect(screen.getByText("Feedback Sent!")).toBeInTheDocument();
    expect(setOpenFeedback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(setOpenFeedback).toHaveBeenCalledWith(false);
  });

  it("shows an error and keeps the typed feedback when the server fails", async () => {
    renderModal(() => Promise.resolve({ ok: false, status: 500 }));

    typeFeedbackAndSend("Helpful");

    expect(
      await screen.findByText(/Couldn't send feedback/),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter your feedback/i)).toHaveValue(
      "Helpful",
    );
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
  });

  it("shows an error when the network request fails", async () => {
    renderModal(() => Promise.reject(new TypeError("Failed to fetch")));

    typeFeedbackAndSend("Helpful");

    expect(
      await screen.findByText(/Couldn't send feedback/),
    ).toBeInTheDocument();
  });
});
