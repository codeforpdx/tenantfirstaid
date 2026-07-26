import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MobilePanel from "../../shared/components/MobilePanel";

/**
 * Helper that overrides window.matchMedia with a controllable listener so
 * tests can simulate the viewport crossing the lg breakpoint.
 */
const installMatchMediaMock = () => {
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const mql = {
    matches: false,
    media: "(min-width: 1024px)",
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) =>
      listeners.add(cb),
    removeEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) =>
      listeners.delete(cb),
    dispatchEvent: () => false,
  };
  const mediaQueryList =
    // oxlint-disable-next-line no-unsafe-type-assertion -- test double implementing only the MediaQueryList members exercised here.
    mql as unknown as MediaQueryList;
  window.matchMedia = vi
    .fn<() => MediaQueryList>()
    .mockReturnValue(mediaQueryList);
  return {
    fireChange: () =>
      act(() => {
        // oxlint-disable-next-line no-unsafe-type-assertion -- jsdom has no MediaQueryListEvent constructor; only `matches` is read.
        const event = { matches: false } as MediaQueryListEvent;
        listeners.forEach((cb) => cb(event));
      }),
  };
};

describe("MobilePanel", () => {
  it("hides children by default (defaultOpen=false)", () => {
    render(
      <MobilePanel title="Frequent Inquiries">
        <p>panel body</p>
      </MobilePanel>,
    );

    // Toggle button is present with collapsed marker.
    const toggle = screen.getByRole("button", { name: /Frequent Inquiries/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    // Children are rendered in DOM (for the grid-rows animation) but inside
    // a collapsed wrapper. aria-expanded is the source of truth for state.
    expect(screen.getByText("panel body")).toBeInTheDocument();
  });

  it("toggles open and closed on click", () => {
    render(
      <MobilePanel title="Features">
        <p>panel body</p>
      </MobilePanel>,
    );

    const toggle = screen.getByRole("button", { name: /Features/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("respects defaultOpen=true", () => {
    render(
      <MobilePanel title="Open By Default" defaultOpen>
        <p>panel body</p>
      </MobilePanel>,
    );

    expect(
      screen.getByRole("button", { name: /Open By Default/i }),
    ).toHaveAttribute("aria-expanded", "true");
  });

  it("resets to defaultOpen when the lg breakpoint changes", () => {
    const { fireChange } = installMatchMediaMock();

    render(
      <MobilePanel title="Resize Test">
        <p>panel body</p>
      </MobilePanel>,
    );

    const toggle = screen.getByRole("button", { name: /Resize Test/i });

    // User opens the panel.
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    // Simulate the viewport crossing the lg breakpoint (e.g., browser resized
    // from mobile to desktop and back). The effect should reset to default.
    fireChange();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
