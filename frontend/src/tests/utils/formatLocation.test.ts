import { describe, it, expect } from "vitest";
import { formatLocation } from "../../shared/utils/formatLocation";

describe("formatLocation", () => {
  it("formats city and state together", () => {
    expect(formatLocation("portland", "or")).toBe("Portland, OR");
  });

  it("capitalizes city with null state", () => {
    expect(formatLocation("eugene", null)).toBe("Eugene");
  });

  it("uppercases state with null city", () => {
    expect(formatLocation(null, "or")).toBe("OR");
  });

  it("returns empty string when both are null", () => {
    expect(formatLocation(null, null)).toBe("");
  });
});
