import { describe, expect, it } from "vitest";
import {
  formatCaseStages,
  formatGeographicScope,
  formatHoursBlock,
  formatProviderTypes,
  formatServiceTypes,
} from "../../shared/utils/formatReferral";

describe("formatReferral", () => {
  it("formats service types", () => {
    expect(formatServiceTypes(["legal_representation"])).toBe(
      "Legal Representation",
    );
    expect(formatServiceTypes(["answer_questions"])).toBe("Answer Questions");
  });

  it("formats provider types", () => {
    expect(formatProviderTypes(["attorney", "licensed_paralegal"])).toBe(
      "Attorney, Licensed Paralegal",
    );
    expect(formatProviderTypes(["non_attorney"])).toBe("Non-Attorney");
  });

  it("formats case stages", () => {
    expect(formatCaseStages(["before_court", "in_court"])).toBe("Any stage");
    expect(formatCaseStages(["in_court"])).toBe("After eviction filed");
    expect(formatCaseStages(["before_court"])).toBe("Before eviction filed");
    expect(formatCaseStages([])).toBeNull();
  });

  it("formats geographic scope", () => {
    expect(formatGeographicScope({ state: "or", cities: [] })).toBe(
      "All of Oregon",
    );
    expect(formatGeographicScope({ state: "or", cities: ["portland"] })).toBe(
      "Portland only",
    );
  });

  it("formats hours blocks", () => {
    expect(
      formatHoursBlock({
        days: ["tuesday", "thursday"],
        start: "09:00",
        end: "17:00",
      }),
    ).toBe("Tue, Thu 9am–5pm");
    expect(
      formatHoursBlock({
        days: ["monday"],
        start: "13:30",
        end: "16:00",
      }),
    ).toBe("Mon 1:30pm–4pm");
  });
});
