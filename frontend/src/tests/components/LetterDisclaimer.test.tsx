import { cleanup, screen } from "@testing-library/react";
import { describe, it, afterEach } from "vitest";
import { renderWithProviders } from "../testUtils";

const renderLetterDisclaimer = async (isOngoing: boolean) => {
  const { default: LetterDisclaimer } =
    await import("../../pages/Letter/components/LetterDisclaimer");
  return renderWithProviders(<LetterDisclaimer isOngoing={isOngoing} />);
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
