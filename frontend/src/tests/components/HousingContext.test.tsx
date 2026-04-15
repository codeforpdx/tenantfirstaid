import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import useHousingContext from "../../hooks/useHousingContext";
import HousingContextProvider from "../../contexts/HousingContext";

function ContextDump() {
  const context = useHousingContext();
  return <pre data-testid="ctx">{JSON.stringify(context)}</pre>;
}

function UpdateLocationButton() {
  const { handleHousingLocation } = useHousingContext();
  return (
    <button
      data-testid="update-loc"
      onClick={() => handleHousingLocation({ city: "portland", state: "or" })}
    >
      update
    </button>
  );
}

function ResetButton() {
  const { handleFormReset } = useHousingContext();
  return (
    <button data-testid="reset" onClick={handleFormReset}>
      reset
    </button>
  );
}

describe("HousingContext", () => {
  it("provides initial context values", () => {
    render(
      <HousingContextProvider>
        <ContextDump />
      </HousingContextProvider>,
    );

    const dump = screen.getByTestId("ctx").textContent ?? "";
    expect(dump).toContain("housingLocation");
    expect(dump).toContain("housingType");
    expect(dump).toContain("tenantTopic");
    expect(dump).toContain("issueDescription");
  });

  it("updates location when handler called", () => {
    render(
      <HousingContextProvider>
        <ContextDump />
        <UpdateLocationButton />
      </HousingContextProvider>,
    );

    expect(screen.getByTestId("ctx").textContent).not.toContain("portland");

    fireEvent.click(screen.getByTestId("update-loc"));

    expect(screen.getByTestId("ctx").textContent).toContain("portland");
    expect(screen.getByTestId("ctx").textContent).toContain('"or"');
  });

  it("resets housingLocation when handleFormReset is called", () => {
    render(
      <HousingContextProvider>
        <ContextDump />
        <UpdateLocationButton />
        <ResetButton />
      </HousingContextProvider>,
    );

    fireEvent.click(screen.getByTestId("update-loc"));
    expect(screen.getByTestId("ctx").textContent).toContain("portland");

    fireEvent.click(screen.getByTestId("reset"));

    expect(screen.getByTestId("ctx").textContent).not.toContain("portland");
  });

  it("throws error when used outside provider", () => {
    const renderOutside = () => render(<ContextDump />);
    expect(renderOutside).toThrow();
  });
});
