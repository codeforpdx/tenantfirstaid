import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it } from "vitest";

const renderLetterDisclaimer = async (isOngoing: boolean) => {
  const { default: LetterDisclaimer } =
    await import("../../pages/Letter/components/LetterDisclaimer");
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
  it("renders Privacy Policy link when onGoing is true", async () => {
    await renderLetterDisclaimer(true);

    const privacyPolicyLink = screen.getByRole("link", {
      name: "to privacy policy",
    });
    expect(privacyPolicyLink).toHaveAttribute("href", "/privacy-policy");
  });

  it("does not render Privacy Policy link when isOngoing is false", async () => {
    await renderLetterDisclaimer(false);

    const privacyPolicyLink = screen.queryByRole("link", {
      name: "to privacy policy",
    });
    expect(privacyPolicyLink).not.toBeInTheDocument();
  });
});
