import type { Location } from "../../../types/models";
import { formatLocation } from "../../../shared/utils/formatLocation";

interface BuildLetterReturnType {
  userMessage: string;
  selectedLocation: Location;
}

/**
 * Strips a partner org name to safe characters, returning "" when nothing remains.
 */
function sanitizeOrg(org: string | undefined): string {
  const CHARACTER_LIMIT = 100; // Limit character count to prevent token overflow
  return (org ?? "")
    .replace(/[^a-zA-Z0-9\s\-_.]/g, "") // Prevent injection attacks
    .replace(/\s+/g, " ") // Normalize whitespace
    .trim()
    .slice(0, CHARACTER_LIMIT);
}

/**
 * Builds the initial letter-generation prompt for a given org and jurisdiction.
 *
 * @param org - Optional partner organization the user was redirected from.
 * @param location - Resolved jurisdiction (city/state) for the letter.
 */
function buildLetterUserMessage(
  org: string | undefined,
  location: Location,
): BuildLetterReturnType {
  const locationString = formatLocation(location.city, location.state);

  const sanitizedOrg = sanitizeOrg(org);

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
    selectedLocation: location,
  };
}

export { buildLetterUserMessage, sanitizeOrg };
