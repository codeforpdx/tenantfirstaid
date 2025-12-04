import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, afterEach } from "vitest";

const renderChatDisclaimer = async (isOngoing: boolean) => {
  const { default: ChatDisclaimer } = await import(
    "../../pages/Chat/components/ChatDisclaimer"
  );
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ChatDisclaimer isOngoing={isOngoing} />
      </BrowserRouter>
    </QueryClientProvider>,
  );
};

describe("ChatDisclaimer component", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders About page link when onGoing is true", async () => {
    const mockIsOngoing = true;
    await renderChatDisclaimer(mockIsOngoing);

    const aboutLink = screen.getByRole("link", { name: "to about page" });
    expect(aboutLink).toHaveAttribute("href", "/about");
  });

  it("does not render About page link when isOngoing is false", async () => {
    const mockIsOngoing = false;
    await renderChatDisclaimer(mockIsOngoing);

    const aboutLink = screen.queryByRole("link", { name: "to about page" });
    expect(aboutLink).not.toBeInTheDocument();
  });
});
