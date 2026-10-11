import { cleanup, screen } from "@testing-library/react";
import { describe, it, afterEach } from "vitest";
import { renderWithProviders } from "../testUtils";

const renderChatDisclaimer = async (isOngoing: boolean) => {
  const { default: ChatDisclaimer } =
    await import("../../pages/Chat/components/ChatDisclaimer");
  return renderWithProviders(<ChatDisclaimer isOngoing={isOngoing} />);
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
