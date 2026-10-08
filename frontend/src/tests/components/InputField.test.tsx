import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HousingContextProvider from "../../contexts/HousingContext";
import InputField from "../../pages/Chat/components/InputField";
import * as streamHelper from "../../pages/Chat/utils/streamHelper";

const renderInputField = (value: string) => {
  const setMessages = vi.fn();
  const setIsLoading = vi.fn();
  const onChange = vi.fn();
  const inputRef = { current: null as HTMLTextAreaElement | null };
  const queryClient = new QueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <InputField
          addMessage={vi.fn()}
          setMessages={setMessages}
          isLoading={false}
          setIsLoading={setIsLoading}
          value={value}
          inputRef={inputRef}
          onChange={onChange}
        />
      </HousingContextProvider>
    </QueryClientProvider>,
  );

  return { setMessages, onChange };
};

describe("InputField keyboard handling", () => {
  it("Enter (without Shift) submits the message", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const { setMessages, onChange } = renderInputField("hello world");

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    // handleSend clears the textarea via onChange and appends a message.
    expect(onChange).toHaveBeenCalled();
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

  it("Enter does not submit while an IME composition is active", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const { setMessages } = renderInputField("你好");

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", isComposing: true });

    expect(setMessages).not.toHaveBeenCalled();
    expect(streamSpy).not.toHaveBeenCalled();

    streamSpy.mockRestore();
  });

  it("Enter does not submit on Safari's IME commit keydown (keyCode 229)", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const { setMessages } = renderInputField("你好");

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", keyCode: 229 });

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
