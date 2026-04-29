import { renderHook } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import useHousingContext from "../../hooks/useHousingContext";
import HousingContextProvider from "../../contexts/HousingContext";

describe("useHousingContext", () => {
  it("throws when used outside HousingContextProvider", () => {
    expect(() => renderHook(() => useHousingContext())).toThrow(
      "useHousing can only be used within HousingContextProvider",
    );
  });

  it("returns context values when used inside HousingContextProvider", () => {
    const { result } = renderHook(() => useHousingContext(), {
      wrapper: HousingContextProvider,
    });

    expect(result.current.housingLocation).toEqual({ city: null, state: null });
    expect(result.current.city).toBeNull();
    expect(result.current.housingType).toBeNull();
    expect(result.current.tenantTopic).toBeNull();
    expect(result.current.issueDescription).toBe("");
    expect(typeof result.current.handleCityChange).toBe("function");
    expect(typeof result.current.handleFormReset).toBe("function");
  });
});
