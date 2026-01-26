import {
  CITY_SELECT_OPTIONS,
  type CitySelectOptionType,
} from "../../../shared/constants/constants";

interface IBuildLetterReturnType {
  userMessage: string;
  selectedLocation: CitySelectOptionType;
}

function buildLetterUserMessage(
  org: string | undefined,
  loc: string | undefined,
): IBuildLetterReturnType | null {
  const selectedLocation = CITY_SELECT_OPTIONS[loc || "oregon"];
  if (selectedLocation === undefined) return null;
  const locationString =
    selectedLocation.city && selectedLocation.state
      ? `${selectedLocation.city}, ${selectedLocation.state}`
      : selectedLocation.city || selectedLocation.state?.toUpperCase() || "";

  const CHARACTER_LIMIT = 100; // Limit character count to prevent token overflow
  const sanitizedOrg = org
    ?.replace(/[^a-zA-Z0-9\s\-_.]/g, "") // Prevent injection attacks
    .replace(/\s+/g, " ") // Normalize whitespace
    .trim()
    .slice(0, CHARACTER_LIMIT);

  const promptParts = [
    sanitizedOrg && `I'm redirected from ${sanitizedOrg}.`,
    `Write a letter to my landlord on housing issues related to my area${locationString ? ` (${locationString})` : ""}.`,
    `Do not ask for additional information until the letter is generated, update the letter as we discuss.`,
    `When the letter is generated, provide instructions for how to copy and paste(formatted) the letter from the browser into a application of my choice,`,
    `the necessary and optional notification / deliveries to the recipient(s), and retention / receipt best practices.`,
    `Also provide instructions if the letter still needs adjustments.`,
    sanitizedOrg &&
      `Have the user follow the steps mentioned from ${sanitizedOrg} first after letter completion, if there were any.`,
  ].filter(Boolean);

  return {
    userMessage: promptParts.join(" ").trim(),
    selectedLocation,
  };
}

export { buildLetterUserMessage };
