import { describe, it, expect } from "vitest";
import { formatLocation } from "../../shared/utils/formatLocation";

describe("formatLocation", () => {
  it("formats city and state together", () => {
    expect(formatLocation("portland", "or")).toBe("Portland, OR");
  });

  it("uppercases state with null city", () => {
    expect(formatLocation(null, "or")).toBe("OR");
  });

  it("omits state when state is 'other'", () => {
    expect(formatLocation(null, "other")).toBe("");
  });

  it("returns only city when state is 'other'", () => {
    expect(formatLocation("portland", "other")).toBe("Portland");
  });
});
