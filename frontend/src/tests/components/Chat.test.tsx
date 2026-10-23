import { screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { Routes, Route } from "react-router-dom";

vi.mock("../../hooks/useLetterContent", () => ({
  useLetterContent: () => ({ letterContent: "" }),
}));

vi.mock("../../hooks/useMessages", () => ({
  default: () => ({
    messages: [],
    setMessages: vi.fn(),
    addMessage: vi.fn(),
  }),
}));

vi.mock("../../pages/Chat/components/MessageWindow", () => ({
  default: () => <div data-testid="message-window" />,
}));

import Chat from "../../Chat";
import RegionNotice from "../../shared/components/RegionNotice";
import { LocationProbe, renderWithProviders } from "../testUtils";

const renderChat = (initialEntry: string) => {
  return renderWithProviders(
    <>
      <RegionNotice />
      <LocationProbe />
      <Routes>
        <Route path="/chat/:state?/:city?" element={<Chat />} />
      </Routes>
    </>,
    { route: initialEntry },
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
