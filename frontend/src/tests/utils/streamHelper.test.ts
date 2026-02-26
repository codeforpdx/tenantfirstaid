import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import {
  streamText,
  type IStreamTextOptions,
} from "../../pages/Chat/utils/streamHelper";

function createMockReader(
  chunks: string[],
): ReadableStreamDefaultReader<Uint8Array> {
  let index = 0;
  return {
    read: vi.fn(async () => {
      if (index >= chunks.length) {
        return { done: true, value: undefined };
      }
      const encoder = new TextEncoder();
      const value = encoder.encode(chunks[index]);
      index++;
      return { done: false, value };
    }),
    releaseLock: vi.fn(),
    cancel: vi.fn(),
    closed: Promise.resolve(undefined),
  } as unknown as ReadableStreamDefaultReader<Uint8Array>;
}

describe("streamText", () => {
  let mockAddMessage: ReturnType<typeof vi.fn>;
  let mockSetMessages: ReturnType<typeof vi.fn>;
  let mockSetIsLoading: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockAddMessage = vi.fn();
    mockSetMessages = vi.fn();
    mockSetIsLoading = vi.fn();
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(Date, "now").mockReturnValue(1000000);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should stream text chunks and update bot message progressively", async () => {
    const mockReader = createMockReader([
      '{"type":"text","text":"Hello"}\n',
      '{"type":"text","text":"world"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    const result = await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "Portland", state: "OR" },
      setIsLoading: mockSetIsLoading,
    } as IStreamTextOptions);

    expect(result).toBe(true);
    expect(mockAddMessage).toHaveBeenCalledWith({
      city: "Portland",
      state: "OR",
    });
    expect(mockSetMessages).toHaveBeenCalledTimes(3); // 1 initial + 2 chunk updates

    // Verify loading state management
    expect(mockSetIsLoading).toHaveBeenCalledWith(true);
    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    expect(mockSetIsLoading).toHaveBeenCalledTimes(2);
  });

  it("should accumulate text correctly and only update the bot message", async () => {
    const mockReader = createMockReader([
      '{"type":"text","text":"First"}\n',
      '{"type":"text","text":" chunk"}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "Portland", state: "OR" },
      setIsLoading: mockSetIsLoading,
    } as IStreamTextOptions);

    const calls = mockSetMessages.mock.calls;
    const updateCall = calls[calls.length - 1][0];
    const existingMessages = [
      new HumanMessage({ content: "User message", id: "999" }),
      new AIMessage({ content: "First", id: "1000001" }),
    ];

    const updated = updateCall(existingMessages);

    expect(updated[0]).toEqual(existingMessages[0]); // User message unchanged
    expect(updated[1].content).toBe(
      '{"type":"text","text":"First"}\n{"type":"text","text":" chunk"}\n',
    ); // Bot message updated with accumulated JSON chunks
  });

  it("should set loading to false even when error occurs and set error message", async () => {
    mockAddMessage.mockRejectedValue(new Error("Stream failed"));

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "Portland", state: "OR" },
      setIsLoading: mockSetIsLoading,
    } as IStreamTextOptions);

    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    expect(console.error).toHaveBeenCalledWith("Error:", expect.any(Error));

    // The empty bot message is added before the API call (calls[0]).
    // The catch block appends the error message as the second setMessages call (calls[1]).
    const updateCall = mockSetMessages.mock.calls[1][0];
    const existingMessages = [
      new HumanMessage({ content: "User message", id: "999" }),
    ];
    const result = updateCall(existingMessages);
    expect(result).toHaveLength(2);
    expect(result[1].text).toContain("Sorry, I encountered an error");
  });

  it("should accumulate reasoning and text chunks in order", async () => {
    const mockReader = createMockReader([
      '{"type":"reasoning","reasoning":"Let me think."}\n',
      '{"type":"text","text":"Here is the answer."}\n',
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "Portland", state: "OR" },
      setIsLoading: mockSetIsLoading,
    } as IStreamTextOptions);

    // 1 initial + 2 chunk updates
    expect(mockSetMessages).toHaveBeenCalledTimes(3);

    const lastCalls = mockSetMessages.mock.calls;
    const lastUpdateCall = lastCalls[lastCalls.length - 1][0];
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    expect(updated[0].content).toBe(
      '{"type":"reasoning","reasoning":"Let me think."}\n{"type":"text","text":"Here is the answer."}\n',
    );
  });

  it("should flush buffer when final chunk has no trailing newline", async () => {
    // The last chunk intentionally omits a trailing newline to exercise the
    // buffer-flush path that runs when done=true and buffer is non-empty.
    const mockReader = createMockReader([
      '{"type":"text","text":"Hello"}\n',
      '{"type":"text","text":"world"}', // no trailing newline
    ]);
    mockAddMessage.mockResolvedValue(mockReader);

    const result = await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "Portland", state: "OR" },
      setIsLoading: mockSetIsLoading,
    } as IStreamTextOptions);

    expect(result).toBe(true);
    expect(mockSetMessages).toHaveBeenCalledTimes(3); // 1 initial + 2 chunk updates

    const lastUpdateCall =
      mockSetMessages.mock.calls[mockSetMessages.mock.calls.length - 1][0];
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    expect(updated[0].content).toBe(
      '{"type":"text","text":"Hello"}\n{"type":"text","text":"world"}\n',
    );
  });

  it("should handle null reader and log error", async () => {
    mockAddMessage.mockResolvedValue(undefined);

    const result = await streamText({
      addMessage: mockAddMessage,
      setMessages: mockSetMessages,
      housingLocation: { city: "Portland", state: "OR" },
      setIsLoading: mockSetIsLoading,
    } as IStreamTextOptions);

    expect(result).toBeUndefined();
    expect(console.error).toHaveBeenCalledWith("Stream reader is unavailable");
    expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    // setMessages is called twice: once to add the empty bot message before the API call,
    // then again to remove it when the reader is unavailable.
    expect(mockSetMessages).toHaveBeenCalledTimes(2);
  });
});
