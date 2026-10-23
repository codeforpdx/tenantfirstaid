import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InputField from "../../pages/Chat/components/InputField";
import * as streamHelper from "../../pages/Chat/utils/streamHelper";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import type { ChatMessage } from "../../shared/types/messages";
import { renderWithProviders } from "../testUtils";

const renderInputField = (value: string, messages: ChatMessage[] = []) => {
  const setMessages = vi.fn();
  const setIsLoading = vi.fn();
  const setValue = vi.fn();
  const inputRef = { current: null as HTMLTextAreaElement | null };
  renderWithProviders(
    <InputField
      messages={messages}
      addMessage={vi.fn()}
      setMessages={setMessages}
      isLoading={false}
      setIsLoading={setIsLoading}
      value={value}
      inputRef={inputRef}
      setValue={setValue}
    />,
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

    // handleSend clears the textarea and appends a message.
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

  it("sends the prior messages plus the new one as history", () => {
    const streamSpy = vi
      .spyOn(streamHelper, "streamText")
      .mockResolvedValue(undefined);
    const prior: ChatMessage[] = [
      new HumanMessage({ content: "first", id: "1" }),
      new AIMessage({ content: '{"type":"text","content":"reply"}', id: "2" }),
    ];
    renderInputField("follow-up", prior);

    const textarea = screen.getByPlaceholderText(/Type your message here/i);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    const { history } = streamSpy.mock.calls[0][0];
    expect(history.map((msg) => msg.text)).toEqual([
      "first",
      '{"type":"text","content":"reply"}',
      "follow-up",
    ]);

    streamSpy.mockRestore();
  });
});
