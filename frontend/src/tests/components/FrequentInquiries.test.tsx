import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import FrequentInquiries from "../../shared/components/FrequentInquiries";
import HousingContextProvider from "../../contexts/HousingContext";

const renderPanel = (entry = "/chat/or") =>
  render(
    <HousingContextProvider>
      <MemoryRouter initialEntries={[entry]}>
        <FrequentInquiries />
      </MemoryRouter>
    </HousingContextProvider>,
  );

describe("FrequentInquiries", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders the first inquiry expanded by default", () => {
    renderPanel();

    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveAttribute("aria-expanded", "true");
    buttons.slice(1).forEach((b) => {
      expect(b).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("collapses the open inquiry when its header is clicked again", () => {
    renderPanel();

    const firstButton = screen.getAllByRole("button")[0];
    expect(firstButton).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(firstButton);
    expect(firstButton).toHaveAttribute("aria-expanded", "false");
  });

  it("keeps only one inquiry open at a time", () => {
    renderPanel();

    const buttons = screen.getAllByRole("button");
    // First is open by default.
    expect(buttons[0]).toHaveAttribute("aria-expanded", "true");

    // Open the second inquiry.
    fireEvent.click(buttons[1]);

    expect(buttons[0]).toHaveAttribute("aria-expanded", "false");
    expect(buttons[1]).toHaveAttribute("aria-expanded", "true");
    buttons.slice(2).forEach((b) => {
      expect(b).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("shows no city-specific note or Statewide label for Oregon at large", () => {
    renderPanel("/chat/or");

    expect(screen.queryByText("Statewide:")).not.toBeInTheDocument();
    expect(screen.queryByText("Portland:")).not.toBeInTheDocument();
    expect(screen.queryByText("Eugene:")).not.toBeInTheDocument();
    expect(screen.queryByText(/68°F/)).not.toBeInTheDocument();
  });

  it("shows Portland-specific guidance on a Portland route", () => {
    renderPanel("/chat/or/portland");

    expect(screen.getAllByText("Portland:").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Statewide:").length).toBeGreaterThan(0);
    expect(screen.queryByText("Eugene:")).not.toBeInTheDocument();
    expect(
      screen.getAllByText(/relocation assistance/i).length,
    ).toBeGreaterThan(0);
  });

  it("shows Eugene-specific guidance on a Eugene route", () => {
    renderPanel("/chat/or/eugene");

    expect(screen.getAllByText("Eugene:").length).toBeGreaterThan(0);
    expect(screen.getByText(/68°F/)).toBeInTheDocument();
    expect(screen.queryByText("Portland:")).not.toBeInTheDocument();
  });

  it("restores the previously opened inquiry after a remount", () => {
    const { unmount } = renderPanel();

    // Open the third inquiry, then simulate a route change by remounting.
    fireEvent.click(screen.getAllByRole("button")[2]);
    unmount();
    renderPanel();

    const buttons = screen.getAllByRole("button");
    expect(buttons[2]).toHaveAttribute("aria-expanded", "true");
    expect(buttons[0]).toHaveAttribute("aria-expanded", "false");
  });

  it("remembers when every inquiry was collapsed", () => {
    const { unmount } = renderPanel();

    // Collapse the default-open first inquiry, then remount.
    fireEvent.click(screen.getAllByRole("button")[0]);
    unmount();
    renderPanel();

    screen.getAllByRole("button").forEach((b) => {
      expect(b).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("renders with the default inquiry open when storage access throws", () => {
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

      const buttons = screen.getAllByRole("button");
      expect(buttons[0]).toHaveAttribute("aria-expanded", "true");

      // Toggling must still work even though persistence fails.
      fireEvent.click(buttons[1]);
      expect(buttons[1]).toHaveAttribute("aria-expanded", "true");
    } finally {
      getItem.mockRestore();
      setItem.mockRestore();
    }
  });

  it("falls back to the first inquiry when the stored index is invalid", () => {
    localStorage.setItem("faqOpenIndex", "999");
    renderPanel();

    expect(screen.getAllByRole("button")[0]).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("links 'draft it here' to the letter page for the active jurisdiction", () => {
    renderPanel("/chat/or/portland");

    // Open the repairs inquiry, whose answer contains the call-to-action.
    fireEvent.click(screen.getAllByRole("button")[1]);

    screen.getAllByText("draft it here").forEach((el) => {
      expect(el.closest("a")).toHaveAttribute("href", "/letter/or/portland");
    });
  });

  it("renders 'draft it here' as plain text on the letter page", () => {
    renderPanel("/letter/or");

    // Open the repairs inquiry, whose answer contains the call-to-action.
    fireEvent.click(screen.getAllByRole("button")[1]);

    screen.getAllByText(/draft it here/).forEach((el) => {
      expect(el.closest("a")).toBeNull();
    });
  });

  it("links 'draft a letter' to the letter page for the active jurisdiction", () => {
    renderPanel("/chat/or/portland");

    // Open the property-damage inquiry, whose answer contains the call-to-action.
    fireEvent.click(screen.getAllByRole("button")[4]);

    screen.getAllByText("draft a letter").forEach((el) => {
      expect(el.closest("a")).toHaveAttribute("href", "/letter/or/portland");
    });
  });

  it("renders 'draft a letter' as plain text on the letter page", () => {
    renderPanel("/letter/or");

    // Open the property-damage inquiry, whose answer contains the call-to-action.
    fireEvent.click(screen.getAllByRole("button")[4]);

    screen.getAllByText(/draft a letter/).forEach((el) => {
      expect(el.closest("a")).toBeNull();
    });
  });

  it("associates each question button with an existing answer panel", () => {
    renderPanel();

    screen.getAllByRole("button").forEach((b) => {
      const panelId = b.getAttribute("aria-controls") ?? "";
      expect(panelId).not.toBe("");
      expect(document.getElementById(panelId)).toBeInTheDocument();
    });
  });

  it("marks collapsed answer panels inert and the open one interactive", () => {
    renderPanel();
    const buttons = screen.getAllByRole("button");

    // The first inquiry is open by default; its panel must stay interactive.
    const openPanel = document.getElementById(
      buttons[0].getAttribute("aria-controls") ?? "",
    );
    expect(openPanel).not.toHaveAttribute("inert");

    // A collapsed inquiry's panel is inert, so its citation links are removed
    // from the tab order and the accessibility tree while hidden.
    const closedPanel = document.getElementById(
      buttons[1].getAttribute("aria-controls") ?? "",
    );
    expect(closedPanel).toHaveAttribute("inert");
  });
});
