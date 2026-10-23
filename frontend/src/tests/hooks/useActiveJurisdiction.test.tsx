import { screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Routes, Route } from "react-router-dom";
import useActiveJurisdiction from "../../hooks/useActiveJurisdiction";
import { LocationProbe, renderWithProviders } from "../testUtils";

function Consumer() {
  const { active, options, selectLocation } = useActiveJurisdiction();
  return (
    <div>
      <span data-testid="active">{active.key}</span>
      <button type="button" onClick={() => selectLocation(options[1])}>
        pick portland
      </button>
    </div>
  );
}

const renderConsumer = (entry: string) =>
  renderWithProviders(
    <>
      <LocationProbe />
      <Routes>
        <Route path="/chat/:state?/:city?" element={<Consumer />} />
        <Route path="/letter/:state?/:city?" element={<Consumer />} />
        <Route path="/about" element={<Consumer />} />
      </Routes>
    </>,
    { route: entry },
  );

describe("useActiveJurisdiction", () => {
  it("derives the active jurisdiction from the URL", () => {
    renderConsumer("/chat/or/portland");
    expect(screen.getByTestId("active")).toHaveTextContent("portland");
  });

  it("defaults to Oregon on a non-feature page", () => {
    renderConsumer("/about");
    expect(screen.getByTestId("active")).toHaveTextContent("oregon");
  });

  it("navigates within the current feature when a location is picked", async () => {
    renderConsumer("/letter/or");
    fireEvent.click(screen.getByText("pick portland"));

    await waitFor(() => {
      expect(screen.getByTestId("pathname")).toHaveTextContent(
        "/letter/or/portland",
      );
    });
  });
});
