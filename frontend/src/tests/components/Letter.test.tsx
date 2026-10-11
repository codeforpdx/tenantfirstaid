import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { Routes, Route } from "react-router-dom";
import { HumanMessage } from "@langchain/core/messages";
import { messagesAddedBy, renderWithProviders } from "../testUtils";

vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: vi.fn(),
}));

vi.mock("../../hooks/useMessages", () => ({
  default: vi.fn(),
}));

vi.mock("../../hooks/useLetterContent", () => ({
  useLetterContent: () => ({ letterContent: "" }),
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: ({ hiddenMessageCount }: { hiddenMessageCount?: number }) => (
    <div data-testid="message-window" data-hidden={hiddenMessageCount} />
  ),
}));

import * as streamHelper from "../../pages/Chat/utils/streamHelper";
import useMessages from "../../hooks/useMessages";

let mockStreamText: ReturnType<typeof vi.fn>;
let mockUseMessages: ReturnType<typeof vi.fn>;

const renderLetter = async (initialEntry = "/letter/or/portland?org=org") => {
  const { default: Letter } = await import("../../Letter");
  return renderWithProviders(
    <Routes>
      <Route path="/letter/:state?/:city?" element={<Letter />} />
    </Routes>,
    { route: initialEntry },
  );
};

describe("Letter component - effect orchestration", () => {
  beforeEach(() => {
    mockStreamText = vi.mocked(streamHelper.streamText);
    mockUseMessages = vi.mocked(useMessages);

    mockStreamText.mockClear();
    mockStreamText.mockResolvedValue(undefined);

    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [],
      setMessages: vi.fn(),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("adds the user message before calling streamText", async () => {
    const callOrder: string[] = [];
    const mockSetMessages = vi.fn(() => {
      callOrder.push("setMessages");
    });
    const mockAddMessage = vi.fn();

    mockStreamText.mockImplementation(async () => {
      callOrder.push("streamText");
      return Promise.resolve(undefined);
    });

    mockUseMessages.mockReturnValue({
      addMessage: mockAddMessage,
      messages: [],
      setMessages: mockSetMessages,
    });

    await renderLetter();

    await waitFor(() => {
      expect(callOrder).toContain("setMessages");
      expect(callOrder).toContain("streamText");
    });

    expect(callOrder.indexOf("setMessages")).toBeLessThan(
      callOrder.indexOf("streamText"),
    );

    expect(mockStreamText).toHaveBeenCalledWith(
      expect.objectContaining({
        addMessage: mockAddMessage,
        setMessages: mockSetMessages,
        housingLocation: { state: "or", city: "portland" },
      }),
    );
    // The message sent to the backend is the one added to the chat.
    const [userMessage] = messagesAddedBy(mockSetMessages);
    expect(userMessage).toBeInstanceOf(HumanMessage);
    expect(mockStreamText.mock.calls[0][0].history).toEqual([userMessage]);
  });

  it("shows loading state before second message arrives", async () => {
    const mockSetMessages = vi.fn();
    const mockAddMessage = vi.fn();

    mockUseMessages.mockReturnValue({
      addMessage: mockAddMessage,
      messages: [new HumanMessage({ content: "hi", id: "1" })],
      setMessages: mockSetMessages,
    });

    await renderLetter();
    await waitFor(() => {
      expect(screen.queryByText("Generating Letter...")).not.toBeNull();
    });
  });

  it("dialog closes when close button clicked", async () => {
    const closeMock = vi.fn();
    HTMLDialogElement.prototype.close = closeMock;

    await renderLetter();

    const closeButton = screen.getByText("Close");

    act(() => {
      fireEvent.click(closeButton);
    });

    expect(closeMock).toHaveBeenCalled();
  });

  it("renders correctly when accessing /letter route directly", async () => {
    await renderLetter("/letter");

    await waitFor(() => {
      expect(mockStreamText).toHaveBeenCalled();
    });
  });

  it("redirects a legacy /letter/:org/:loc link to the canonical form", async () => {
    await renderLetter("/letter/PartnerOrg/eugene");

    await waitFor(() => {
      expect(mockStreamText).toHaveBeenCalledWith(
        expect.objectContaining({
          housingLocation: { state: "or", city: "eugene" },
        }),
      );
    });
  });

  it("redirects an out-of-state /letter link to Oregon", async () => {
    await renderLetter("/letter/wa/seattle");

    await waitFor(() => {
      expect(mockStreamText).toHaveBeenCalledWith(
        expect.objectContaining({
          housingLocation: { state: "or", city: null },
        }),
      );
    });
  });

  it("shows the redirect notice for a partner org link", async () => {
    await renderLetter("/letter/or?org=legal-aid");

    expect(
      screen.getByText(/It'll take a few seconds/, { selector: "p" })
        .textContent,
    ).toMatch(/redirected/);
  });

  it("omits the redirect notice when the org sanitizes to empty", async () => {
    await renderLetter("/letter/or?org=%21%21");

    expect(
      screen.getByText(/It'll take a few seconds/, { selector: "p" })
        .textContent,
    ).not.toMatch(/redirected/);
  });

  it("adds error message when stream ends without calling onDone", async () => {
    // Simulate a dropped connection: streamText resolves but never calls onDone.
    const mockSetMessages = vi.fn();
    mockStreamText.mockImplementation(() => Promise.resolve());

    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [],
      setMessages: mockSetMessages,
    });

    await renderLetter();

    await waitFor(() => {
      expect(mockStreamText).toHaveBeenCalled();
    });

    const addedTexts = messagesAddedBy(mockSetMessages).map((msg) => msg.text);
    // Should not add the instruction message (no letter was cleanly generated).
    expect(addedTexts.some((text) => text.includes("initial template"))).toBe(
      false,
    );
    // Should add the error message so the user isn't left with an empty panel.
    expect(addedTexts.some((text) => text.includes("Unable to generate"))).toBe(
      true,
    );
  });

  it("hides the setup prompt and letter response from the message list", async () => {
    await renderLetter();

    const messageWindow = await screen.findByTestId(
      "message-window",
      {},
      { timeout: 2000 },
    );
    expect(messageWindow).toHaveAttribute("data-hidden", "2");
  });

  it("gives every message it adds a distinct id within the same millisecond", async () => {
    const dateNow = vi.spyOn(Date, "now").mockReturnValue(1000);
    try {
      const mockSetMessages = vi.fn();
      mockUseMessages.mockReturnValue({
        addMessage: vi.fn(),
        messages: [],
        setMessages: mockSetMessages,
      });

      await renderLetter();
      await waitFor(() => {
        expect(messagesAddedBy(mockSetMessages)).toHaveLength(2);
      });

      const ids = messagesAddedBy(mockSetMessages).map((msg) => msg.id);
      expect(new Set(ids).size).toBe(ids.length);
    } finally {
      dateNow.mockRestore();
    }
  });
});
