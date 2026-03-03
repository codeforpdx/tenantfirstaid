import { describe, it, expect } from "vitest";
import { buildChatUserMessage } from "../../pages/Chat/utils/formHelper";
import type { ILocation } from "../../types/HousingTypes";

describe("buildChatUserMessage", () => {
  it("builds message with all fields populated", () => {
    const location: ILocation = {
      city: "portland",
      state: "or",
    };
    const housingType = "Apartment/House Rental";
    const tenantTopic = "Eviction and Notices";
    const issueDescription = "My landlord served me an eviction notice";

    const result = buildChatUserMessage(
      location,
      housingType,
      tenantTopic,
      issueDescription,
    );

    expect(result.userMessage).toContain("Portland, OR");
    expect(result.userMessage).toContain("Apartment/House Rental");
    expect(result.userMessage).toContain("Eviction and Notices");
    expect(result.userMessage).toContain(
      "My landlord served me an eviction notice",
    );
  });

  it("handles null city gracefully", () => {
    const location: ILocation = {
      city: null,
      state: "or",
    };
    const housingType = "Apartment/House Rental";
    const tenantTopic = "Rent Issues";
    const issueDescription = "Rent increase";

    const result = buildChatUserMessage(
      location,
      housingType,
      tenantTopic,
      issueDescription,
    );

    expect(result.userMessage).toContain("OR.");
    expect(result.userMessage).not.toContain("null");
  });

  it("includes all prompt parts", () => {
    const location: ILocation = {
      city: "portland",
      state: "or",
    };
    const housingType = "Apartment/House Rental";
    const tenantTopic = "Eviction and Notices";
    const issueDescription = "My landlord served me an eviction notice";

    const result = buildChatUserMessage(
      location,
      housingType,
      tenantTopic,
      issueDescription,
    );

    const message = result.userMessage;

    expect(message).toContain(
      "I'm in Portland, OR. I live in Apartment/House Rental. My issue is on Eviction and Notices: My landlord served me an eviction notice",
    );
  });
});
