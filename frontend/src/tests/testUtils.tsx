import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import type { Mock } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useLocation } from "react-router-dom";
import HousingContextProvider from "../contexts/HousingContext";
import type { ChatMessage } from "../shared/types/messages";

/**
 * Renders `ui` inside the app's query, housing-context, and router providers.
 * Pass a `<Routes>` tree as `ui` when the component reads route params.
 */
export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <HousingContextProvider>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </HousingContextProvider>
    </QueryClientProvider>,
  );
}

/** Renders the current pathname so tests can assert on redirects. */
export function LocationProbe() {
  const { pathname } = useLocation();
  return <div data-testid="pathname">{pathname}</div>;
}

/** Returns a stream reader that yields each chunk in order, then finishes. */
export function createMockReader(
  chunks: string[],
): ReadableStreamDefaultReader<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;
  return {
    read: vi.fn(async () => {
      if (index >= chunks.length) {
        return { done: true, value: undefined };
      }
      return { done: false, value: encoder.encode(chunks[index++]) };
    }),
    releaseLock: vi.fn(),
    cancel: vi.fn(),
    closed: Promise.resolve(undefined),
  } as unknown as ReadableStreamDefaultReader<Uint8Array>;
}

/** Returns a stream reader whose reads never resolve, simulating a stream still in progress. */
export function createPendingReader(): ReadableStreamDefaultReader<Uint8Array> {
  return {
    read: () => new Promise(() => {}),
  } as unknown as ReadableStreamDefaultReader<Uint8Array>;
}

/**
 * Collects the messages appended by each functional update passed to a
 * mocked `setMessages`, by applying every updater to an empty list.
 */
export function messagesAddedBy(setMessages: Mock): ChatMessage[] {
  return setMessages.mock.calls
    .map(([update]) => update)
    .filter((update) => typeof update === "function")
    .flatMap((update) => update([]));
}
