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
import { IMessage } from "../../hooks/useMessages";

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
  useLetterContent: () => ({ letterContent: "" }),
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: () => <div data-testid="message-window" />,
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
import HousingContextProvider from "../../contexts/HousingContext";
import { CITY_SELECT_OPTIONS } from "../../shared/constants/constants";

let mockStreamText: ReturnType<typeof vi.fn>;
let mockUseMessages: ReturnType<typeof vi.fn>;

const renderLetter = async () => {
  const { default: Letter } = await import("../../Letter");
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <MemoryRouter initialEntries={["/letter/org/portland"]}>
          <Routes>
            <Route path="/letter/:org/:loc" element={<Letter />} />
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
        housingLocation: expect.objectContaining(
          CITY_SELECT_OPTIONS["portland"],
        ),
      }),
    );
  });

  it("shows loading state before second message arrives", async () => {
    const mockSetMessages = vi.fn();
    const mockAddMessage = vi.fn();

    mockUseMessages.mockReturnValue({
      addMessage: mockAddMessage,
      messages: [{ role: "user", content: "hi", messageId: "1" }],
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
    const { default: Letter } = await import("../../Letter");
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <HousingContextProvider>
          <MemoryRouter initialEntries={["/letter"]}>
            <Routes>
              <Route path="/letter" element={<Letter />} />
            </Routes>
          </MemoryRouter>
        </HousingContextProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(mockStreamText).toHaveBeenCalled();
    });
  });

  it("shows error message when stream fails", async () => {
    const mockSetMessages = vi.fn();
    mockStreamText.mockResolvedValue(undefined);

    mockUseMessages.mockReturnValue({
      addMessage: vi.fn(),
      messages: [],
      setMessages: mockSetMessages,
    });

    await renderLetter();

    await waitFor(() => {
      expect(mockSetMessages).toHaveBeenCalledWith(expect.any(Function));
    });

    const setMessagesCall = mockSetMessages.mock.calls.find((call) => {
      const result = call[0]([]);
      return result.some((msg: IMessage) =>
        msg.content.includes("Unable to generate letter"),
      );
    });
    expect(setMessagesCall).toBeDefined();
  });
});
