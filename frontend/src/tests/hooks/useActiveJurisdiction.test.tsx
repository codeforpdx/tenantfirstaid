import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter, Routes, Route, useLocation } from "react-router";
import useActiveJurisdiction from "../../hooks/useActiveJurisdiction";
import HousingContextProvider from "../../contexts/HousingContext";

function LocationProbe() {
  const { pathname } = useLocation();
  return <div data-testid="pathname">{pathname}</div>;
}

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
  render(
    <HousingContextProvider>
      <MemoryRouter initialEntries={[entry]}>
        <LocationProbe />
        <Routes>
          <Route path="/chat/:state?/:city?" element={<Consumer />} />
          <Route path="/letter/:state?/:city?" element={<Consumer />} />
          <Route path="/about" element={<Consumer />} />
        </Routes>
      </MemoryRouter>
    </HousingContextProvider>,
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
