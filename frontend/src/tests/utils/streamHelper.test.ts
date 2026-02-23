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

    const updateCall = mockSetMessages.mock.calls.at(-1)[0];
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

    const errorUpdateCall = mockSetMessages.mock.calls.find(([updater]) => {
      const result = updater([new AIMessage({ content: "", id: "1000001" })]);
      return result[0].content.includes("Sorry, I encountered an error");
    });

    expect(errorUpdateCall).toBeDefined();
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

    const lastUpdateCall = mockSetMessages.mock.calls.at(-1)[0];
    const updated = lastUpdateCall([
      new AIMessage({ content: "", id: "1000001" }),
    ]);
    expect(updated[0].content).toBe(
      '{"type":"reasoning","reasoning":"Let me think."}\n{"type":"text","text":"Here is the answer."}\n',
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
  });
});
