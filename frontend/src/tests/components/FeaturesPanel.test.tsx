import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FeaturesPanel from "../../shared/components/FeaturesPanel";

// Both MobilePanel and useIsMobile query window.matchMedia.
// matches: false → (max-width:1023px) is false → desktop (isMobile = false).
const stubMatchMedia = (matches: boolean) =>
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches,
      addEventListener:
        vi.fn<(type: string, listener: (...args: unknown[]) => void) => void>(),
      removeEventListener:
        vi.fn<(type: string, listener: (...args: unknown[]) => void) => void>(),
    }),
  );

stubMatchMedia(false);

const renderPanel = (disclaimer = <p>Disclaimer text</p>) =>
  render(<FeaturesPanel disclaimer={disclaimer} />);

describe("FeaturesPanel", () => {
  beforeEach(() => {
    localStorage.clear();
    stubMatchMedia(false); // reset to desktop before each test
  });

  it("renders open by default", () => {
    renderPanel();
    expect(getToggle()).toHaveAttribute("aria-expanded", "true");
  });

  it("renders features content", () => {
    renderPanel();
    expect(
      screen.getByText(/instant answers to common rental questions/i),
    ).toBeInTheDocument();
  });

  it("renders the disclaimer prop", () => {
    renderPanel(<p>Custom disclaimer</p>);
    expect(screen.getByText("Custom disclaimer")).toBeInTheDocument();
  });

  it("closes when the toggle button is clicked", () => {
    renderPanel();
    fireEvent.click(getToggle());
    expect(getToggle()).toHaveAttribute("aria-expanded", "false");
  });

  it("reopens when the toggle button is clicked a second time", () => {
    renderPanel();
    fireEvent.click(getToggle());
    fireEvent.click(getToggle());
    expect(getToggle()).toHaveAttribute("aria-expanded", "true");
  });

  it("applies opacity class to content when closed", () => {
    const { container } = renderPanel();
    fireEvent.click(getToggle());
    const contentWrapper = container.querySelector(".lg\\:opacity-0");
    expect(contentWrapper).toBeInTheDocument();
  });

  it("removes opacity class from content when open", () => {
    const { container } = renderPanel();
    const contentWrapper = container.querySelector(".lg\\:opacity-0");
    expect(contentWrapper).not.toBeInTheDocument();
  });

  it("sets content inert when closed on desktop", () => {
    const { container } = renderPanel();
    fireEvent.click(getToggle());
    expect(container.querySelector("#features-panel-content")).toHaveAttribute(
      "inert",
    );
  });

  it("renders open and still toggles when storage access throws", () => {
    const getItem = vi
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("storage disabled");
      });
    const setItem = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("storage disabled");
      });
    try {
      renderPanel();
      expect(getToggle()).toHaveAttribute("aria-expanded", "true");

      // Toggling must still work even though persistence fails.
      fireEvent.click(getToggle());
      expect(getToggle()).toHaveAttribute("aria-expanded", "false");
    } finally {
      getItem.mockRestore();
      setItem.mockRestore();
    }
  });

  it("does not set content inert on mobile even when desktop panel state is closed", () => {
    // Simulate the bug scenario: panel was previously closed on desktop and
    // persisted to localStorage, then the user opens the page on mobile.
    localStorage.setItem("featuresPanelOpen", "false");
    stubMatchMedia(true); // (max-width:1023px) matches → isMobile = true
    const { container } = renderPanel();
    expect(
      container.querySelector("#features-panel-content"),
    ).not.toHaveAttribute("inert");
  });
});

function getToggle() {
  return screen.getByRole("button", { name: /toggle features panel/i });
}
