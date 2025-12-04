import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, afterEach } from "vitest";

const renderLetterDisclaimer = async (isOngoing: boolean) => {
  const { default: LetterDisclaimer } = await import(
    "../../pages/Letter/components/LetterDisclaimer"
  );
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <LetterDisclaimer isOngoing={isOngoing} />
      </BrowserRouter>
    </QueryClientProvider>,
  );
};

describe("LetterDisclaimer component", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders Privacy Policy link when onGoing is true", async () => {
    const mockIsOngoing = true;
    await renderLetterDisclaimer(mockIsOngoing);

    const privacyPolicyLink = screen.getByRole("link", {
      name: "to privacy policy",
    });
    expect(privacyPolicyLink).toHaveAttribute("href", "/privacy-policy");
  });

  it("does not render Privacy Policy link when isOngoing is false", async () => {
    const mockIsOngoing = false;
    await renderLetterDisclaimer(mockIsOngoing);

    const privacyPolicyLink = screen.queryByRole("link", {
      name: "to privacy policy",
    });
    expect(privacyPolicyLink).not.toBeInTheDocument();
  });
});
