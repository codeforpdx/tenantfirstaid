import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InitializationForm from "../../pages/Chat/components/InitializationForm";
import HousingContextProvider from "../../contexts/HousingContext";
import useSyncJurisdiction from "../../hooks/useSyncJurisdiction";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { HumanMessage } from "@langchain/core/messages";
import type { ChatMessage } from "../../shared/types/messages";

vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: vi.fn<typeof streamText>(),
}));

const mockSetMessages = vi.fn<React.Dispatch<React.SetStateAction<ChatMessage[]>>>();

// Mirror Chat: the jurisdiction comes from the URL (navbar picker), not the
// form, so seed it from the route params the way Chat does.
function FormHarness() {
  useSyncJurisdiction();
  return (
    <InitializationForm addMessage={vi.fn<Props["addMessage"]>()} setMessages={mockSetMessages} />
  );
}

const renderInitializationForm = (entry = "/chat") => {
  mockSetMessages.mockClear();
  render(
    <MemoryRouter initialEntries={[entry]}>
      <HousingContextProvider>
        <Routes>
          <Route path="/chat/:state?/:city?" element={<FormHarness />} />
        </Routes>
      </HousingContextProvider>
    </MemoryRouter>,
  );
};

/** Extracts the HumanMessage added by the first setMessages call. */
function getSubmittedMessage(): HumanMessage | undefined {
  const updater = mockSetMessages.mock.calls.find(
    (call) => typeof call[0] === "function",
  )?.[0];
  if (!updater) return undefined;
  const result: ChatMessage[] = updater([]);
  return result.find((msg): msg is HumanMessage => msg instanceof HumanMessage);
}

describe("InitializationForm", () => {
  it("renders the textarea and action buttons", () => {
    renderInitializationForm();

    expect(
      screen.getByPlaceholderText(/briefly describe your specific/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "enter chat" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
  });

  it("does not render housing type or tenant topic selectors", () => {
    renderInitializationForm();

    expect(screen.queryByLabelText("housing type")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("tenant topic")).not.toBeInTheDocument();
  });

  it("does not render a Generate Letter button", () => {
    renderInitializationForm();

    expect(
      screen.queryByRole("link", { name: "generate letter" }),
    ).not.toBeInTheDocument();
  });

  it("prefixes location to the description when both are present", async () => {
    renderInitializationForm("/chat/or/portland");

    fireEvent.change(
      screen.getByPlaceholderText(/briefly describe your specific/i),
      { target: { value: "My landlord won't fix the heat" } },
    );

    fireEvent.submit(
      screen.getByRole("button", { name: "enter chat" }).closest("form")!,
    );

    await waitFor(() => expect(mockSetMessages).toHaveBeenCalled());

    const msg = getSubmittedMessage();
    expect(msg).toBeDefined();
    expect(msg!.content).toBe(
      "I'm in Portland, OR. My landlord won't fix the heat",
    );
  });

  it("prefixes state-only location when no city is set", async () => {
    renderInitializationForm("/chat/or");

    fireEvent.change(
      screen.getByPlaceholderText(/briefly describe your specific/i),
      { target: { value: "My deposit was not returned" } },
    );

    fireEvent.submit(
      screen.getByRole("button", { name: "enter chat" }).closest("form")!,
    );

    await waitFor(() => expect(mockSetMessages).toHaveBeenCalled());

    const msg = getSubmittedMessage();
    expect(msg).toBeDefined();
    expect(msg!.content).toBe("I'm in OR. My deposit was not returned");
  });

  it("sends only the location when description is empty", async () => {
    renderInitializationForm("/chat/or/eugene");

    fireEvent.submit(
      screen.getByRole("button", { name: "enter chat" }).closest("form")!,
    );

    await waitFor(() => expect(mockSetMessages).toHaveBeenCalled());

    const msg = getSubmittedMessage();
    expect(msg).toBeDefined();
    expect(msg!.content).toBe("I'm in Eugene, OR.");
  });
});
