import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
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
import {
  DevicePrivacyContext,
  type DevicePrivacy,
} from "../../contexts/DevicePrivacyContext";

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
            new HumanMessage({ content: "New question", id: "new" }),
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

async function renderConversation(path: string, privacy: DevicePrivacy | null) {
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
          <DevicePrivacyContext.Provider value={privacy}>
            <RouterProvider router={router} />
          </DevicePrivacyContext.Provider>
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
    "The response was interrupted. Please send your question again.";
  const key = "chat_messages:portland";

  it("adds one UI-only notice for a restored unanswered question", async () => {
    const history = [{ type: "human", content: "Old question", id: "old" }];
    sessionStorage.setItem(key, JSON.stringify(history));
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      body: null,
    } as Response);
    const view = await renderConversation("/chat/or/portland", "private");

    expect(screen.getByTestId("messages").textContent).toBe(
      `Old question|${notice}`,
    );
    expect(JSON.parse(sessionStorage.getItem(key) ?? "[]")).toEqual(history);
    expect(fetchSpy).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());
    const request = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body));
    expect(request.messages).toEqual([
      { role: "human", content: "Old question", id: "old" },
    ]);

    view.unmount();
    await renderConversation("/chat/or/portland", "private");
    expect(screen.getByTestId("messages").textContent).toBe(
      `Old question|${notice}`,
    );
  });

  it("does not show a notice for a completed restored response", async () => {
    sessionStorage.setItem(
      key,
      JSON.stringify([
        { type: "human", content: "Old question", id: "old" },
        { type: "ai", content: "Answer", id: "answer", complete: true },
      ]),
    );
    await renderConversation("/chat/or/portland", "private");
    expect(screen.getByTestId("messages")).not.toHaveTextContent(notice);
  });

  it("does not treat a newly submitted question as interrupted", async () => {
    await renderConversation("/chat/or/portland", "private");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    expect(screen.getByTestId("messages").textContent).toBe("New question");
  });
});

describe.each([
  { page: "chat", path: "/chat/or/portland", key: "chat_messages:portland" },
  {
    page: "letter",
    path: "/letter/or/portland?org=partner",
    key: "letter_messages:portland,partner",
  },
])("$page message persistence", ({ path, key }) => {
  it.each(["public", null] as const)(
    "keeps messages in memory with choice %s",
    async (privacy) => {
      const oldHistory = JSON.stringify([
        { type: "human", content: "Old question", id: "old" },
      ]);
      sessionStorage.setItem(key, oldHistory);
      const writeSpy = vi.spyOn(Storage.prototype, "setItem");
      const view = await renderConversation(path, privacy);

      expect(screen.getByTestId("messages")).not.toHaveTextContent(
        "Old question",
      );
      expect(
        await screen.findByTestId("messages", {}, { timeout: 2000 }),
      ).not.toHaveTextContent("New question");
      fireEvent.click(screen.getByRole("button", { name: "Add message" }));
      expect(screen.getByTestId("messages")).toHaveTextContent("New question");
      expect(writeSpy).not.toHaveBeenCalled();
      expect(sessionStorage.getItem(key)).toBe(oldHistory);

      view.unmount();
      await renderConversation(path, privacy);
      expect(
        await screen.findByTestId("messages", {}, { timeout: 2000 }),
      ).not.toHaveTextContent("New question");
    },
  );

  it("restores and persists messages on private devices", async () => {
    sessionStorage.setItem(
      key,
      JSON.stringify([{ type: "human", content: "Old question", id: "old" }]),
    );
    const view = await renderConversation(path, "private");
    expect(screen.getByTestId("messages")).toHaveTextContent("Old question");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    expect(JSON.parse(sessionStorage.getItem(key) ?? "[]")).toEqual([
      { type: "human", content: "Old question", id: "old" },
      { type: "human", content: "New question", id: "new" },
    ]);

    view.unmount();
    await renderConversation(path, "private");
    expect(screen.getByTestId("messages")).toHaveTextContent(
      "Old question|New question",
    );
  });

  it("drops public messages after leaving and returning to the page", async () => {
    const { router } = await renderConversation(path, "public");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    await act(async () => {
      await router.navigate("/about");
    });
    await act(async () => {
      await router.navigate(path);
    });
    expect(
      await screen.findByTestId("messages", {}, { timeout: 2000 }),
    ).not.toHaveTextContent("New question");
  });

  it("clears public messages and aborts the old request when jurisdiction changes", async () => {
    let signal: AbortSignal | null | undefined;
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((_url, init) => {
        signal = init?.signal;
        return new Promise<Response>(() => {});
      });
    const { router } = await renderConversation(path, "public");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());
    expect(signal?.aborted).toBe(false);

    await act(async () => {
      await router.navigate(path.replace("portland", "eugene"));
    });

    expect(
      await screen.findByTestId("messages", {}, { timeout: 2000 }),
    ).not.toHaveTextContent("New question");
    expect(signal?.aborted).toBe(true);
  });
});
