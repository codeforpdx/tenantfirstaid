import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { createRef } from "react";
import InputField from "../../pages/Chat/components/InputField";
import HousingContextProvider from "../../contexts/HousingContext";

vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: vi.fn(),
}));

function renderInputField(
  overrides: Partial<React.ComponentProps<typeof InputField>> = {},
) {
  const inputRef = createRef<HTMLTextAreaElement>();
  const props = {
    addMessage: vi.fn(),
    setMessages: vi.fn(),
    isLoading: false,
    setIsLoading: vi.fn(),
    value: "",
    inputRef,
    onChange: vi.fn(),
    ...overrides,
  };

  render(
    <HousingContextProvider>
      <InputField {...props} />
    </HousingContextProvider>,
  );

  return props;
}

describe("InputField", () => {
  it("renders a textarea and Send button", () => {
    renderInputField();

    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("disables the textarea and button when isLoading is true", () => {
    renderInputField({ isLoading: true });

    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "..." })).toBeDisabled();
  });

  it("disables the Send button when value is empty or whitespace", () => {
    renderInputField({ value: "   " });
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("enables the Send button when value has content", () => {
    renderInputField({ value: "hello" });
    expect(screen.getByRole("button", { name: "Send" })).not.toBeDisabled();
  });

  it("calls onChange when the textarea value changes", () => {
    const onChange = vi.fn();
    renderInputField({ onChange });

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "new text" },
    });

    expect(onChange).toHaveBeenCalled();
  });

  it("clears input and adds user message when Send is clicked with content", async () => {
    const setMessages = vi.fn();
    const onChange = vi.fn();
    renderInputField({ setMessages, onChange, value: "hello" });

    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ target: { value: "" } }),
      );
      expect(setMessages).toHaveBeenCalled();
    });
  });

  it("does not send on Enter if value is empty", () => {
    const setMessages = vi.fn();
    renderInputField({ setMessages, value: "" });

    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });

    expect(setMessages).not.toHaveBeenCalled();
  });
});
