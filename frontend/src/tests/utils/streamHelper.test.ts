import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
  type Mock,
} from "vitest";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { streamText } from "../../pages/Chat/utils/streamHelper";
import type { ChatMessage } from "../../shared/types/messages";
import type { Location } from "../../types/models";

type AddMessage = (
  args: Location,
) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>;
type SetMessages = React.Dispatch<React.SetStateAction<ChatMessage[]>>;
type SetIsLoading = React.Dispatch<React.SetStateAction<boolean>>;
type Updater = (prev: ChatMessage[]) => ChatMessage[];

function createMockReader(
  chunks: string[],
): ReadableStreamDefaultReader<Uint8Array> {
  let index = 0;
  return {
    read: vi.fn<() => Promise<ReadableStreamReadResult<Uint8Array>>>(() => {
      if (index >= chunks.length) {
        return Promise.resolve({ done: true, value: undefined });
      }
      const encoder = new TextEncoder();
      const value = encoder.encode(chunks[index]);
      index++;
      return Promise.resolve({ done: false, value });
    }),
    releaseLock: vi.fn<() => void>(),
    cancel: vi.fn<() => Promise<never>>(),
    closed: Promise.resolve(undefined),
  };
}

describe("streamText", () => {
  let mockAddMessage: Mock<AddMessage>;
  let mockSetMessages: Mock<SetMessages>;
  let mockSetIsLoading: Mock<SetIsLoading>;

  beforeEach(() => {
    mockAddMessage = vi.fn<AddMessage>();
    mockSetMessages = vi.fn<SetMessages>();
    mockSetIsLoading = vi.fn<SetIsLoading>();
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(Date, "now").mockReturnValue(1000000);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should stream text chunks and update bot message progressively", async () => {
    const mockReader = createMockReader([
      '{"type":"text","content":"Hello"}\n',
      '{"type":"text","content":"world"}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      setIsLoading: mockSetIsLoading,
    });

    expect(mockAddMessage).toHaveBeenCalledWith({
      city: "portland",
      state: "or",
    });
    expect(mockSetMessages).toHaveBeenCalledTimes(3); // 1 initial + 2 chunk updates
    expect(mockSetIsLoading).toHaveBeenCalledWith(true);
    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    expect(mockSetIsLoading).toHaveBeenCalledTimes(2);
  });

  it("should accumulate text correctly and only update the bot message", async () => {
    const mockReader = createMockReader([
      '{"type":"text","content":"First"}\n',
      '{"type":"text","content":" chunk"}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      setIsLoading: mockSetIsLoading,
    });

    const calls = mockSetMessages.mock.calls;
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
    const updateCall = calls[calls.length - 1][0] as Updater;
    const existingMessages = [
      new HumanMessage({ content: "User message", id: "999" }),
      new AIMessage({ content: "First", id: "1000001" }),
    ];

    const updated = updateCall(existingMessages);

    expect(updated[0]).toEqual(existingMessages[0]);
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText only ever produces AIMessage bot messages in these updates.
    expect((updated[1] as AIMessage).content).toBe(
      '{"type":"text","content":"First"}\n{"type":"text","content":" chunk"}\n',
    );
  });

  it("should set loading to false even when error occurs and set error message", async () => {
    mockAddMessage.mockRejectedValue(new Error("Stream failed"));

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      setIsLoading: mockSetIsLoading,
    });

    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    expect(console.error).toHaveBeenCalledWith("Error:", expect.any(Error));

    // The empty bot message is added before the API call (calls[0]).
    // The catch block appends the error message as the second setMessages call (calls[1]).
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
    const updateCall = mockSetMessages.mock.calls[1][0] as Updater;
    const existingMessages = [
      new HumanMessage({ content: "User message", id: "999" }),
    ];
    const result = updateCall(existingMessages);
    expect(result).toHaveLength(2);
    expect(result[1].text).toContain("Sorry, I encountered an error");
  });

  it("should accumulate reasoning and text chunks in order", async () => {
    const mockReader = createMockReader([
      '{"type":"reasoning","content":"Let me think."}\n',
      '{"type":"text","content":"Here is the answer."}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      setIsLoading: mockSetIsLoading,
    });

    // 1 initial + 2 chunk updates (done chunk does not trigger setMessages)
    expect(mockSetMessages).toHaveBeenCalledTimes(3);

    const lastCalls = mockSetMessages.mock.calls;
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
    const lastUpdateCall = lastCalls[lastCalls.length - 1][0] as Updater;
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText only ever produces AIMessage bot messages in these updates.
    expect((updated[0] as AIMessage).content).toBe(
      '{"type":"reasoning","content":"Let me think."}\n{"type":"text","content":"Here is the answer."}\n',
    );
  });

  it("should flush buffer when final chunk has no trailing newline", async () => {
    // The last chunk intentionally omits a trailing newline to exercise the
    // buffer-flush path that runs when done=true and buffer is non-empty.
    // This simulates a dropped connection (no done chunk from backend).
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const mockReader = createMockReader([
      '{"type":"text","content":"Hello"}\n',
      '{"type":"text","content":"world"}', // no trailing newline, no done chunk
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      setIsLoading: mockSetIsLoading,
    });

    expect(mockSetMessages).toHaveBeenCalledTimes(3); // 1 initial + 2 chunk updates

    const lastUpdateCall =
      // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
      mockSetMessages.mock.calls[
        mockSetMessages.mock.calls.length - 1
      ][0] as Updater;
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText only ever produces AIMessage bot messages in these updates.
    expect((updated[0] as AIMessage).content).toBe(
      '{"type":"text","content":"Hello"}\n{"type":"text","content":"world"}\n',
    );
  });

  it("should handle null reader and log error", async () => {
    mockAddMessage.mockResolvedValue(undefined);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      setIsLoading: mockSetIsLoading,
    });

    expect(console.error).toHaveBeenCalledWith("Stream reader is unavailable");
    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    // setMessages is called twice: once to add the empty placeholder, once to replace
    // it with a UiMessage error so the letter page slice(2) can show the error.
    expect(mockSetMessages).toHaveBeenCalledTimes(2);
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
    const replaceCall = mockSetMessages.mock.calls[1][0] as Updater;
    const result2 = replaceCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    expect(result2[0].text).toContain("Sorry, I encountered an error");
  });

  it("should call onDone when done chunk is received", async () => {
    const mockOnDone = vi.fn<() => void>();
    const mockReader = createMockReader([
      '{"type":"text","content":"Hello"}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      onDone: mockOnDone,
    });

    expect(mockOnDone).toHaveBeenCalledTimes(1);
  });

  it("should not call onDone when stream ends without a done chunk", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const mockOnDone = vi.fn<() => void>();
    const mockReader = createMockReader([
      '{"type":"text","content":"Hello"}\n',
      // No done chunk — simulates dropped connection.
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
      onDone: mockOnDone,
    });

    expect(mockOnDone).not.toHaveBeenCalled();
    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining("done chunk"),
    );
  });

  it("should not append done chunk to bot message content", async () => {
    const mockReader = createMockReader([
      '{"type":"text","content":"Actual content"}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
    });

    const lastUpdateCall =
      // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
      mockSetMessages.mock.calls[
        mockSetMessages.mock.calls.length - 1
      ][0] as Updater;
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText only ever produces AIMessage bot messages in these updates.
    expect((updated[0] as AIMessage).content).not.toContain('"type":"done"');
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText only ever produces AIMessage bot messages in these updates.
    expect((updated[0] as AIMessage).content).toContain('"type":"text"');
  });

  it("should append letter chunk to bot message content", async () => {
    const mockReader = createMockReader([
      '{"type":"text","content":"Here is your letter."}\n',
      '{"type":"letter","content":"Dear Landlord,"}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
    });

    const lastUpdateCall =
      // oxlint-disable-next-line no-unsafe-type-assertion -- streamText always calls setMessages with an updater function here.
      mockSetMessages.mock.calls[
        mockSetMessages.mock.calls.length - 1
      ][0] as Updater;
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    // oxlint-disable-next-line no-unsafe-type-assertion -- streamText only ever produces AIMessage bot messages in these updates.
    expect((updated[0] as AIMessage).content).toContain(
      '{"type":"letter","content":"Dear Landlord,"}',
    );
  });

  it("should not call setMessages for the done chunk line", async () => {
    const mockReader = createMockReader([
      '{"type":"text","content":"Hello"}\n',
      '{"type":"end_of_stream"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "portland", state: "or" },
    });

    // 1 initial + 1 text chunk = 2 calls; done chunk adds no call.
    expect(mockSetMessages).toHaveBeenCalledTimes(2);
  });
});
