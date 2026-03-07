import { formatLocation } from "../../../shared/utils/formatLocation";
import type { Location } from "../../../types/models";
import type {
  HousingType,
  TenantTopic,
} from "../../../shared/constants/constants";

interface ChatFormReturnType {
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
  loc: Location,
  housingType: HousingType | null,
  tenantTopic: TenantTopic | null,
  issueDescription: string,
): ChatFormReturnType {
  const locationString = formatLocation(loc.city, loc.state);

  const promptParts = [
    ...(locationString ? [`I'm in ${locationString}.`] : []),
    `I live in ${housingType}.`,
    `My issue is on ${tenantTopic}: ${issueDescription === "" ? "Non-specific." : issueDescription}`,
  ];

  return {
    userMessage: promptParts.join(" ").trim(),
  };
}

export { buildChatUserMessage };
