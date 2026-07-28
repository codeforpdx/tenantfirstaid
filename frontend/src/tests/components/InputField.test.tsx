import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HousingContextProvider from "../../contexts/HousingContext";
import InputField from "../../pages/Chat/components/InputField";
import * as streamHelper from "../../pages/Chat/utils/streamHelper";
import type { ChatMessage } from "../../shared/types/messages";
import type { Location } from "../../types/models";

const renderInputField = (value: string) => {
  const setMessages =
    vi.fn<React.Dispatch<React.SetStateAction<ChatMessage[]>>>();
  const setIsLoading = vi.fn<React.Dispatch<React.SetStateAction<boolean>>>();
  const setValue = vi.fn<(value: string) => void>();
  const inputRef = { current: null as HTMLTextAreaElement | null };
  const queryClient = new QueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <InputField
          addMessage={vi.fn<
            (
              args: Location,
            ) => Promise<ReadableStreamDefaultReader<Uint8Array> | undefined>
          >()}
          setMessages={setMessages}
          isLoading={false}
          setIsLoading={setIsLoading}
          value={value}
          inputRef={inputRef}
          setValue={setValue}
        />
      </HousingContextProvider>
    </QueryClientProvider>,
  );

  return { setMessages, setValue };
};

describe("InputField keyboard handling", () => {
  it("Enter (without Shift) submits the message", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const { setMessages, setValue } = renderInputField("hello world");

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    // handleSend clears the textarea via setValue and appends a message.
    expect(setValue).toHaveBeenCalledWith("");
    expect(setMessages).toHaveBeenCalled();
    expect(streamSpy).toHaveBeenCalled();

    streamSpy.mockRestore();
  });

  it("Shift+Enter does not submit (lets the newline through)", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const { setMessages } = renderInputField("draft message");

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    expect(setMessages).not.toHaveBeenCalled();
    expect(streamSpy).not.toHaveBeenCalled();

    streamSpy.mockRestore();
  });

  it("Enter does nothing when the input is empty", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const { setMessages } = renderInputField("   ");

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    expect(setMessages).not.toHaveBeenCalled();
    expect(streamSpy).not.toHaveBeenCalled();

    streamSpy.mockRestore();
  });
});
