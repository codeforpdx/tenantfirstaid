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
import type { ChatMessage } from "../../shared/types/messages";
import Chat from "../../Chat";
import Letter from "../../Letter";
import HousingContextProvider from "../../contexts/HousingContext";
import {
  DevicePrivacyContext,
  type DevicePrivacy,
} from "../../contexts/DevicePrivacyContext";

// Keep letter generation out of these tests while using the real message hook.
vi.mock("../../hooks/useLetterContent", () => ({
  useLetterContent: () => ({ letterContent: "Draft letter" }),
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

function renderConversation(path: string, privacy: DevicePrivacy | null) {
  const router = createMemoryRouter(
    [
      { path: "/chat/:state?/:city?", element: <Chat /> },
      { path: "/letter/:state?/:city?", element: <Letter /> },
      { path: "/about", element: <div>About</div> },
    ],
    { initialEntries: [path] },
  );
  const view = render(
    <QueryClientProvider client={new QueryClient()}>
      <HousingContextProvider>
        <DevicePrivacyContext.Provider value={privacy}>
          <RouterProvider router={router} />
        </DevicePrivacyContext.Provider>
      </HousingContextProvider>
    </QueryClientProvider>,
  );
  return { ...view, router };
}

beforeEach(() => {
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
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
    (privacy) => {
      const oldHistory = JSON.stringify([
        { type: "human", content: "Old question", id: "old" },
      ]);
      sessionStorage.setItem(key, oldHistory);
      const writeSpy = vi.spyOn(Storage.prototype, "setItem");
      const view = renderConversation(path, privacy);

      expect(screen.getByTestId("messages")).toBeEmptyDOMElement();
      fireEvent.click(screen.getByRole("button", { name: "Add message" }));
      expect(screen.getByTestId("messages")).toHaveTextContent("New question");
      expect(writeSpy).not.toHaveBeenCalled();
      expect(sessionStorage.getItem(key)).toBe(oldHistory);

      view.unmount();
      renderConversation(path, privacy);
      expect(screen.getByTestId("messages")).toBeEmptyDOMElement();
    },
  );

  it("restores and persists messages on private devices", () => {
    sessionStorage.setItem(
      key,
      JSON.stringify([{ type: "human", content: "Old question", id: "old" }]),
    );
    const view = renderConversation(path, "private");
    expect(screen.getByTestId("messages")).toHaveTextContent("Old question");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    expect(JSON.parse(sessionStorage.getItem(key) ?? "[]")).toEqual([
      { type: "human", content: "Old question", id: "old" },
      { type: "human", content: "New question", id: "new" },
    ]);

    view.unmount();
    renderConversation(path, "private");
    expect(screen.getByTestId("messages")).toHaveTextContent(
      "Old question|New question",
    );
  });

  it("drops public messages after leaving and returning to the page", async () => {
    const { router } = renderConversation(path, "public");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    await act(async () => {
      await router.navigate("/about");
    });
    await act(async () => {
      await router.navigate(path);
    });
    expect(screen.getByTestId("messages")).toBeEmptyDOMElement();
  });

  it("clears public messages and aborts the old request when jurisdiction changes", async () => {
    let signal: AbortSignal | null | undefined;
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((_url, init) => {
        signal = init?.signal;
        return new Promise<Response>(() => {});
      });
    const { router } = renderConversation(path, "public");
    fireEvent.click(screen.getByRole("button", { name: "Add message" }));
    fireEvent.click(screen.getByRole("button", { name: "Send request" }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledOnce());
    expect(signal?.aborted).toBe(false);

    await act(async () => {
      await router.navigate(path.replace("portland", "eugene"));
    });

    expect(screen.getByTestId("messages")).toBeEmptyDOMElement();
    expect(signal?.aborted).toBe(true);
  });
});
