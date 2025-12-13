import { ILocation } from "../../../contexts/HousingContext";

interface IChatFormReturnType {
  userMessage: string;
}

/**
 * Builds the initial user message for the AI based on housing context
 *
 * @param loc - User's housing location (city and state)
 * @param housingType - Type of housing (e.g., "Apartment/House Rental")
 * @param tenantTopic - Topic of inquiry (e.g., "Eviction and Notices")
 * @param issueDescription - User's specific issue or question
 * @returns Object containing the formatted user message
 */
function buildChatUserMessage(
  loc: ILocation,
  housingType: string | null,
  tenantTopic: string | null,
  issueDescription: string,
): IChatFormReturnType {
  const locationString =
    loc.city && loc.state
      ? `${loc.city}, ${loc.state}`
      : loc.city || loc.state || "";

  const promptParts = [
    `I'm in ${locationString ? `${locationString}` : ""}.`,
    `I live in ${housingType}.`,
    `My issue is on ${tenantTopic}: ${issueDescription === "" ? "Non-specific." : issueDescription}`,
  ];

  return {
    userMessage: promptParts.join(" ").trim(),
  };
}

export { buildChatUserMessage };
