import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { HumanMessage } from "@langchain/core/messages";
import type { Dispatch, SetStateAction } from "react";
import { StrictMode } from "react";
import type { ChatMessage } from "../../shared/types/messages";
import Chat from "../../Chat";
import Letter from "../../Letter";
import HousingContextProvider from "../../contexts/HousingContext";

// Complete generation without a network request while using the real message hook.
vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: async ({ onDone }: { onDone?: () => void }) => onDone?.(),
}));

vi.mock("../../pages/Letter/components/LetterGenerationDialog", () => ({
  default: () => null,
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: ({
    messages,
    setMessages,
    addMessage,
  }: {
    messages: ChatMessage[];
    setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
    addMessage: (location: { state: string; city: string }) => Promise<unknown>;
  }) => (
    <div>
      <div data-testid="messages">
        {messages.map((message) => message.text).join("|")}
      </div>
      <button
        onClick={() =>
          setMessages((previous) => [
            ...previous,
            new HumanMessage({ content: "New message", id: "new" }),
          ])
        }
      >
        Add message
      </button>
      <button
        onClick={() => {
          void addMessage({ state: "or", city: "portland" });
        }}
      >
        Send request
      </button>
    </div>
  ),
}));

async function renderConversation(path: string) {
  const router = createMemoryRouter(
    [
      { path: "/chat/:state?/:city?", element: <Chat /> },
      { path: "/letter/:state?/:city?", element: <Letter /> },
      { path: "/about", element: <div>About</div> },
    ],
    { initialEntries: [path] },
  );
  const view = render(
    <StrictMode>
      <QueryClientProvider client={new QueryClient()}>
        <HousingContextProvider>
          <RouterProvider router={router} />
        </HousingContextProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
  await screen.findByTestId("messages", {}, { timeout: 2000 });
  return { ...view, router };
}

beforeEach(() => {
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("chat response interruption notice", () => {
  const notice =
    "The response was interrupted. Please send your message again.";
  const key = "chat_messages:portland";

  it("adds one UI-only notice for a restored unanswered message", async () => {
    const history = [{ type: "human", content: "Old message", id: "old" }];
    sessionStorage.setItem(key, JSON.stringify(history));
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      body: null,
    } as Response);
    const view = await renderConversation("/chat/or/portland");

    expect(screen.getByTestId("messages").textContent).toBe(
      `Old message|${notice}`,
    );
    expect(JSON.parse(sessionStorage.getItem(key) ?? "[]")).toEqual(history);
    expect(fetchSpy).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());
    const request = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body));
    expect(request.messages).toEqual([
      { role: "human", content: "Old message", id: "old" },
    ]);

    view.unmount();
    await renderConversation("/chat/or/portland");
    expect(screen.getByTestId("messages").textContent).toBe(
      `Old message|${notice}`,
    );
  });

  it("does not show a notice for a completed restored response", async () => {
    sessionStorage.setItem(
      key,
      JSON.stringify([
        { type: "human", content: "Old message", id: "old" },
        { type: "ai", content: "Answer", id: "answer", complete: true },
      ]),
    );
    await renderConversation("/chat/or/portland");
    expect(screen.getByTestId("messages")).not.toHaveTextContent(notice);
  });

  it("does not treat a newly submitted message as interrupted", async () => {
    await renderConversation("/chat/or/portland");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    expect(screen.getByTestId("messages").textContent).toBe("New message");
  });
});
