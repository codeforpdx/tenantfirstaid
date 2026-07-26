import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";

vi.mock("../../hooks/useLetterContent", () => ({
  useLetterContent: () => ({ letterContent: "" }),
}));

vi.mock("../../hooks/useMessages", () => ({
  default: () => ({
    messages: [],
    setMessages: vi.fn<(messages: import("../../../shared/types/messages").ChatMessage[]) => void>(),
    addMessage: vi.fn<(location: import("../../../types/models").Location) => Promise<ReadableStreamDefaultReader<Uint8Array> | null>>(),
  }),
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: () => <div data-testid="message-window" />,
}));

import Chat from "../../Chat";
import RegionNotice from "../../shared/components/RegionNotice";
import HousingContextProvider from "../../contexts/HousingContext";

function LocationProbe() {
  const { pathname } = useLocation();
  return <div data-testid="pathname">{pathname}</div>;
}

const renderChat = (initialEntry: string) => {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <HousingContextProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <RegionNotice />
          <LocationProbe />
          <Routes>
            <Route path="/chat/:state?/:city?" element={<Chat />} />
          </Routes>
        </MemoryRouter>
      </HousingContextProvider>
    </QueryClientProvider>,
  );
};

describe("Chat out-of-state guard", () => {
  it("renders a supported jurisdiction without redirecting", () => {
    renderChat("/chat/or/portland");
    expect(screen.getByTestId("pathname")).toHaveTextContent(
      "/chat/or/portland",
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("redirects an out-of-state URL to Oregon and shows a notice", async () => {
    renderChat("/chat/ca/los-angeles");

    await waitFor(() => {
      expect(screen.getByTestId("pathname")).toHaveTextContent("/chat/or");
    });
    expect(screen.getByRole("status")).toHaveTextContent(/only covers Oregon/i);
  });
});
