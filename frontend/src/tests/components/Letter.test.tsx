import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  vi,
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  beforeAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import type { ChatMessage } from "../../shared/types/messages";

beforeAll(() => {
  if (!("scrollTo" in HTMLElement.prototype)) {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    HTMLElement.prototype.scrollTo = function () {};
  }
  HTMLDialogElement.prototype.showModal = vi.fn();
  HTMLDialogElement.prototype.close = vi.fn();
});

vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: vi.fn(),
}));

vi.mock("../../hooks/useMessages", () => ({
  default: vi.fn(),
}));

vi.mock("../../hooks/useLetterContent", () => ({
  useLetterContent: vi.fn(),
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: ({ clearMessages }: { clearMessages: () => void }) => (
    <div data-testid="message-window">
      <button onClick={clearMessages}>Clear Letter</button>
    </div>
  ),
}));

vi.mock("../../shared/utils/reloadPage", () => ({
  reloadPage: vi.fn(),
}));

vi.mock("../../LetterGenerationDialog", () => ({
  default: ({ ref }: { ref: React.Ref<HTMLDialogElement | null> }) => (
    <dialog ref={ref} open>
      <p>Some content</p>
      <button>close</button>
    </dialog>
  ),
}));

import * as streamHelper from "../../pages/Chat/utils/streamHelper";
import useMessages from "../../hooks/useMessages";
import { useLetterContent } from "../../hooks/useLetterContent";
import { reloadPage } from "../../shared/utils/reloadPage";
import HousingContextProvider from "../../contexts/HousingContext";

let mockStreamText: ReturnType<typeof vi.fn>;
let mockUseMessages: ReturnType<typeof vi.fn>;
let mockUseLetterContent: ReturnType<typeof vi.fn>;
let mockReloadPage: ReturnType<typeof vi.fn>;

const renderLetter = async (initialEntry = "/letter/or/portland?org=org") => {
  const { default: Letter } = await import("../../Letter");
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/letter/:state?/:city?" element={<Letter />} />
          </Routes>
        </MemoryRouter>
      </HousingContextProvider>
    </QueryClientProvider>,
  );
};

describe("Letter component - effect orchestration", () => {
  beforeEach(() => {
    mockStreamText = vi.mocked(streamHelper.streamText);
    mockUseMessages = vi.mocked(useMessages);
    mockUseLetterContent = vi.mocked(useLetterContent);
    mockReloadPage = vi.mocked(reloadPage);

    mockStreamText.mockClear();
    mockStreamText.mockResolvedValue(undefined);
    mockUseLetterContent.mockReturnValue({ letterContent: "" });

    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [],
      setMessages: vi.fn(),
      clearMessages: vi.fn(),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("first effect adds user message before second effect calls streamText", async () => {
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

  it("restores a completed letter without generating it again", async () => {
    const mockSetMessages = vi.fn();
    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [
        new HumanMessage({ content: "Generate my letter", id: "1" }),
        new AIMessage({
          content: '{"type":"letter","content":"Dear Landlord,"}\n',
          id: "2",
        }),
      ],
      setMessages: mockSetMessages,
      clearMessages: vi.fn(),
    });
    mockUseLetterContent.mockReturnValue({
      letterContent: "Dear Landlord,",
    });

    await renderLetter();

    await waitFor(() => {
      expect(screen.getByTestId("message-window")).not.toBeNull();
    });

    expect(screen.queryByText("Generating Letter...")).toBeNull();
    expect(mockSetMessages).not.toHaveBeenCalled();
    expect(mockStreamText).not.toHaveBeenCalled();
  });

  it("retries an incomplete restored session without duplicating the prompt", async () => {
    const mockSetMessages = vi.fn();
    const restoredPrompt = new HumanMessage({
      content: "Generate my letter",
      id: "1",
    });
    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [restoredPrompt],
      setMessages: mockSetMessages,
      clearMessages: vi.fn(),
    });

    await renderLetter();

    await waitFor(() => {
      expect(mockStreamText).toHaveBeenCalled();
    });

    const duplicatedPrompt = mockSetMessages.mock.calls.some((call) => {
      const update = call[0];
      if (typeof update !== "function") return false;
      const updatedMessages = update([restoredPrompt]) as ChatMessage[];
      return updatedMessages.filter((message) => message.type === "human")
        .length > 1;
    });
    expect(duplicatedPrompt).toBe(false);
  });

  it("clears the letter before reloading the page", async () => {
    const callOrder: string[] = [];
    const mockClearMessages = vi.fn(() => {
      callOrder.push("clear");
    });
    mockReloadPage.mockImplementation(() => {
      callOrder.push("reload");
    });
    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [
        new HumanMessage({ content: "Generate my letter", id: "1" }),
        new AIMessage({
          content: '{"type":"letter","content":"Dear Landlord,"}\n',
          id: "2",
        }),
      ],
      setMessages: vi.fn(),
      clearMessages: mockClearMessages,
    });
    mockUseLetterContent.mockReturnValue({
      letterContent: "Dear Landlord,",
    });

    await renderLetter();
    fireEvent.click(screen.getByText("Clear Letter"));

    expect(callOrder).toEqual(["clear", "reload"]);
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

    // Should not add the instruction message (no letter was cleanly generated).
    const addedInstructionMessage = mockSetMessages.mock.calls.find((call) => {
      const result = call[0]([]);
      return result.some(
        (msg: ChatMessage) =>
          "text" in msg && msg.text.includes("initial template"),
      );
    });
    expect(addedInstructionMessage).toBeUndefined();

    // Should add the error message so the user isn't left with an empty panel.
    const addedErrorMessage = mockSetMessages.mock.calls.find((call) => {
      const result = call[0]([]);
      return result.some(
        (msg: ChatMessage) =>
          "text" in msg && msg.text.includes("Unable to generate"),
      );
    });
    expect(addedErrorMessage).toBeDefined();
  });
});
